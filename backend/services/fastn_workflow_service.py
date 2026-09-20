import logging
from typing import Any

import httpx

from core.config import settings

logger = logging.getLogger(__name__)


class FastnWorkflowConfigurationError(RuntimeError):
    pass


class FastnWorkflowRequestError(RuntimeError):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class FastnWorkflowService:
    def __init__(
        self,
        workflow_id: str | None = None,
        api_base_url: str | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        self.workflow_id = workflow_id or settings.FASTN_WORKFLOW_ID
        self.api_base_url = (api_base_url or settings.FASTN_API_BASE_URL).rstrip("/")
        self.client = client

    async def execute(
        self,
        payload: dict[str, Any],
        tenant_id: str | None = None,
        installation_id: str | None = None,
    ) -> dict[str, Any]:
        if not settings.FASTN_API_KEY:
            raise FastnWorkflowConfigurationError("FASTN_API_KEY is not configured.")

        url = f"{self.api_base_url}/api/v1/workflows/{self.workflow_id}/execute"
        headers = {
            "Content-Type": "application/json",
            settings.FASTN_AUTH_HEADER: self._auth_value(),
        }
        if tenant_id:
            headers[settings.FASTN_TENANT_HEADER] = str(tenant_id)
        if tenant_id and installation_id is None:
            installation_id = await self.resolve_installation_id(str(tenant_id))
        if installation_id:
            headers[settings.FASTN_INSTALLATION_HEADER] = str(installation_id)
        if settings.FASTN_API_KEY.startswith("fsk_test_"):
            headers["X-fastn-Test-Mode"] = "true"

        logger.info(
            "fastn.execute.start workflow_id=%s tenant_id=%s payload=%s",
            self.workflow_id,
            tenant_id or "",
            self._payload_summary(payload),
        )
        logger.info(
            "fastn.execute.headers workflow_id=%s tenant_header=%s tenant_id=%s test_mode=%s",
            self.workflow_id,
            settings.FASTN_TENANT_HEADER,
            tenant_id or "",
            bool(headers.get("X-fastn-Test-Mode")),
        )
        logger.info(
            "fastn.execute.installation workflow_id=%s tenant_id=%s installation_id=%s",
            self.workflow_id,
            tenant_id or "",
            installation_id or "",
        )

        try:
            if self.client is not None:
                response = await self.client.post(url, json={"input": payload}, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=settings.FASTN_TIMEOUT_SECONDS) as client:
                    response = await client.post(url, json={"input": payload}, headers=headers)
        except httpx.HTTPError as exc:
            logger.exception(
                "fastn.execute.network_error workflow_id=%s tenant_id=%s",
                self.workflow_id,
                tenant_id or "",
            )
            raise FastnWorkflowRequestError(
                status_code=502,
                detail=f"Fastn workflow request failed: {exc}",
            ) from exc

        if response.status_code >= 400:
            logger.warning(
                "fastn.execute.error workflow_id=%s tenant_id=%s status_code=%s detail=%s",
                self.workflow_id,
                tenant_id or "",
                response.status_code,
                self._error_detail(response),
            )
            raise FastnWorkflowRequestError(
                status_code=response.status_code,
                detail=self._error_detail(response),
            )

        body = self._response_body(response)
        logger.info(
            "fastn.execute.success workflow_id=%s tenant_id=%s status_code=%s response=%s",
            self.workflow_id,
            tenant_id or "",
            response.status_code,
            self._response_summary(body),
        )
        return body

    async def create_embed_token(self, customer_id: str) -> dict[str, Any]:
        if not settings.FASTN_API_KEY:
            raise FastnWorkflowConfigurationError("FASTN_API_KEY is not configured.")

        url = f"{self.api_base_url}/api/v1/embed/token"
        headers = {
            "Content-Type": "application/json",
            settings.FASTN_AUTH_HEADER: self._auth_value(),
            "x-org-id": str(customer_id),
        }
        if settings.FASTN_API_KEY.startswith("fsk_test_"):
            headers["X-fastn-Test-Mode"] = "true"

        logger.info("fastn.embed_token.start customer_id=%s", customer_id)
        try:
            if self.client is not None:
                response = await self.client.post(url, json={}, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=settings.FASTN_TIMEOUT_SECONDS) as client:
                    response = await client.post(url, json={}, headers=headers)
        except httpx.HTTPError as exc:
            logger.exception("fastn.embed_token.network_error customer_id=%s", customer_id)
            raise FastnWorkflowRequestError(502, f"Fastn embed token request failed: {exc}") from exc

        if response.status_code >= 400:
            logger.warning(
                "fastn.embed_token.error customer_id=%s status_code=%s detail=%s",
                customer_id,
                response.status_code,
                self._error_detail(response),
            )
            raise FastnWorkflowRequestError(response.status_code, self._error_detail(response))
        body = self._response_body(response)
        data = body.get("data", body)
        logger.info(
            "fastn.embed_token.success customer_id=%s returned_end_org_id=%s expires_in=%s token_present=%s",
            customer_id,
            data.get("endOrgId") if isinstance(data, dict) else "",
            data.get("expiresIn") if isinstance(data, dict) else "",
            bool(data.get("token")) if isinstance(data, dict) else False,
        )
        return body

    async def create_embed_token_for_customer(
        self,
        customer_id: str,
        display_name: str | None = None,
    ) -> dict[str, Any]:
        try:
            return await self.create_embed_token(customer_id)
        except FastnWorkflowRequestError as exc:
            if exc.status_code != 404 or "x-org-id does not match" not in exc.detail:
                raise

            logger.info(
                "fastn.embed_token.customer_missing customer_id=%s detail=%s",
                customer_id,
                exc.detail,
            )
            await self.ensure_customer_org(
                customer_id,
                (display_name or f"SEO Agent User {customer_id[:8]}")[:200],
            )
            logger.info("fastn.embed_token.retry_after_create customer_id=%s", customer_id)
            return await self.create_embed_token(customer_id)

    async def ensure_customer_org(self, customer_ref: str, display_name: str) -> str:
        """Return the Fastn org id for an app user, creating the end-org once."""
        if not settings.FASTN_API_KEY:
            raise FastnWorkflowConfigurationError("FASTN_API_KEY is not configured.")

        headers = {settings.FASTN_AUTH_HEADER: self._auth_value()}
        if settings.FASTN_API_KEY.startswith("fsk_test_"):
            headers["X-fastn-Test-Mode"] = "true"
        logger.info(
            "fastn.org.lookup.start external_ref=%s display_name=%s",
            customer_ref,
            display_name,
        )
        try:
            if self.client is not None:
                response = await self.client.get(f"{self.api_base_url}/api/v1/orgs", headers=headers)
            else:
                async with httpx.AsyncClient(timeout=settings.FASTN_TIMEOUT_SECONDS) as client:
                    response = await client.get(f"{self.api_base_url}/api/v1/orgs", headers=headers)
        except httpx.HTTPError as exc:
            logger.exception("fastn.org.lookup.network_error external_ref=%s", customer_ref)
            raise FastnWorkflowRequestError(502, f"Fastn organization lookup failed: {exc}") from exc
        if response.status_code >= 400:
            logger.warning(
                "fastn.org.lookup.error external_ref=%s status_code=%s detail=%s",
                customer_ref,
                response.status_code,
                self._error_detail(response),
            )
            raise FastnWorkflowRequestError(response.status_code, self._error_detail(response))

        organizations = self._response_body(response).get("data", [])
        logger.info(
            "fastn.org.lookup.response external_ref=%s org_count=%s",
            customer_ref,
            len(organizations) if isinstance(organizations, list) else 0,
        )
        existing = next(
            (
                item for item in organizations
                if str(item.get("externalRef") or item.get("external_ref") or "") == str(customer_ref)
            ),
            None,
        )
        if existing:
            org_id = str(
                existing.get("endOrgId")
                or existing.get("end_org_id")
                or existing.get("orgId")
                or existing.get("id")
            )
            logger.info(
                "fastn.org.lookup.hit external_ref=%s end_org_id=%s",
                customer_ref,
                org_id,
            )
            return org_id

        payload = {
            "name": display_name[:200],
            "slug": f"seo-agent-{str(customer_ref).replace('-', '')[:24]}".lower(),
            "external_ref": str(customer_ref),
            "type": "end_org",
            "plan": "free",
        }
        logger.info(
            "fastn.org.create.start external_ref=%s slug=%s",
            customer_ref,
            payload["slug"],
        )
        try:
            if self.client is not None:
                response = await self.client.post(
                    f"{self.api_base_url}/api/v1/orgs", json=payload,
                    headers={**headers, "Content-Type": "application/json"},
                )
            else:
                async with httpx.AsyncClient(timeout=settings.FASTN_TIMEOUT_SECONDS) as client:
                    response = await client.post(
                        f"{self.api_base_url}/api/v1/orgs", json=payload,
                        headers={**headers, "Content-Type": "application/json"},
                    )
        except httpx.HTTPError as exc:
            logger.exception("fastn.org.create.network_error external_ref=%s", customer_ref)
            raise FastnWorkflowRequestError(502, f"Fastn organization creation failed: {exc}") from exc
        if response.status_code >= 400:
            logger.warning(
                "fastn.org.create.error external_ref=%s status_code=%s detail=%s",
                customer_ref,
                response.status_code,
                self._error_detail(response),
            )
            raise FastnWorkflowRequestError(response.status_code, self._error_detail(response))
        created = self._response_body(response).get("data", {})
        org_id = created.get("endOrgId") or created.get("end_org_id") or created.get("orgId") or created.get("id")
        if not org_id:
            logger.error("fastn.org.create.missing_id external_ref=%s", customer_ref)
            raise FastnWorkflowRequestError(502, "Fastn did not return a customer organization id.")
        logger.info("fastn.org.create.success external_ref=%s end_org_id=%s", customer_ref, org_id)
        return str(org_id)

    async def resolve_installation_id(self, end_org_id: str) -> str:
        if not settings.FASTN_WIDGET_ID:
            return ""
        if not settings.FASTN_API_KEY:
            raise FastnWorkflowConfigurationError("FASTN_API_KEY is not configured.")

        headers = {settings.FASTN_AUTH_HEADER: self._auth_value()}
        if settings.FASTN_API_KEY.startswith("fsk_test_"):
            headers["X-fastn-Test-Mode"] = "true"
        params = {
            "end_org_id": end_org_id,
            "widget_id": settings.FASTN_WIDGET_ID,
        }
        logger.info(
            "fastn.installation.lookup.start end_org_id=%s widget_id=%s",
            end_org_id,
            settings.FASTN_WIDGET_ID,
        )
        try:
            if self.client is not None:
                response = await self.client.get(
                    f"{self.api_base_url}/api/v1/installations",
                    params=params,
                    headers=headers,
                )
            else:
                async with httpx.AsyncClient(timeout=settings.FASTN_TIMEOUT_SECONDS) as client:
                    response = await client.get(
                        f"{self.api_base_url}/api/v1/installations",
                        params=params,
                        headers=headers,
                    )
        except httpx.HTTPError as exc:
            logger.exception("fastn.installation.lookup.network_error end_org_id=%s", end_org_id)
            raise FastnWorkflowRequestError(502, f"Fastn installation lookup failed: {exc}") from exc

        if response.status_code >= 400:
            detail = self._error_detail(response)
            logger.warning(
                "fastn.installation.lookup.error end_org_id=%s status_code=%s detail=%s",
                end_org_id,
                response.status_code,
                detail,
            )
            raise FastnWorkflowRequestError(
                response.status_code,
                detail,
            )

        body = self._response_body(response)
        installations = body.get("data", body)
        if not isinstance(installations, list):
            logger.info("fastn.installation.lookup.empty end_org_id=%s response_keys=%s", end_org_id, sorted(body.keys()))
            return ""

        active = next(
            (
                item for item in installations
                if item.get("status") == "active"
                and item.get("endOrgId") == end_org_id
                and item.get("widgetId") == settings.FASTN_WIDGET_ID
            ),
            None,
        )
        selected = active or next(
            (
                item for item in installations
                if item.get("endOrgId") == end_org_id
                and item.get("widgetId") == settings.FASTN_WIDGET_ID
            ),
            None,
        )
        installation_id = str(selected.get("id", "")) if selected else ""
        logger.info(
            "fastn.installation.lookup.success end_org_id=%s widget_id=%s installation_id=%s count=%s",
            end_org_id,
            settings.FASTN_WIDGET_ID,
            installation_id,
            len(installations),
        )
        return installation_id

    async def list_github_repositories(self, tenant_id: str) -> list[dict[str, Any]]:
        options = await self.destination_options(tenant_id)
        repositories = options.get("repositories")
        return repositories if isinstance(repositories, list) else []

    async def list_google_spreadsheets(self, tenant_id: str) -> list[dict[str, Any]]:
        options = await self.destination_options(tenant_id)
        spreadsheets = options.get("spreadsheets")
        return spreadsheets if isinstance(spreadsheets, list) else []

    async def destination_options(self, tenant_id: str) -> dict[str, Any]:
        logger.info(
            "fastn.destinations.start workflow_id=%s tenant_id=%s",
            settings.FASTN_DESTINATIONS_WORKFLOW_ID,
            tenant_id,
        )
        result = await FastnWorkflowService(
            workflow_id=settings.FASTN_DESTINATIONS_WORKFLOW_ID,
            api_base_url=self.api_base_url,
            client=self.client,
        ).execute({}, tenant_id=tenant_id)
        options = self._workflow_result(result)
        logger.info(
            "fastn.destinations.success tenant_id=%s repositories=%s spreadsheets=%s github_login=%s errors=%s",
            tenant_id,
            len(options.get("repositories", [])) if isinstance(options.get("repositories"), list) else 0,
            len(options.get("spreadsheets", [])) if isinstance(options.get("spreadsheets"), list) else 0,
            ((options.get("accounts") or {}).get("github") or {}).get("login", ""),
            sorted((options.get("errors") or {}).keys()) if isinstance(options.get("errors"), dict) else [],
        )
        return options

    def _auth_value(self) -> str:
        scheme = settings.FASTN_AUTH_SCHEME.strip()
        if scheme:
            return f"{scheme} {settings.FASTN_API_KEY}"
        return settings.FASTN_API_KEY

    @staticmethod
    def _payload_summary(payload: dict[str, Any]) -> dict[str, Any]:
        tasks = payload.get("tasks")
        return {
            "keys": sorted(payload.keys()),
            "source": payload.get("source", ""),
            "siteUrl": payload.get("siteUrl", ""),
            "reportId": payload.get("reportId", ""),
            "github": f"{payload.get('github_owner', '')}/{payload.get('github_repo', '')}".strip("/"),
            "spreadsheetId": payload.get("spreadsheetId") or payload.get("google_spreadsheet_id", ""),
            "spreadsheetName": payload.get("spreadsheetName") or payload.get("google_spreadsheet_name", ""),
            "taskCount": len(tasks) if isinstance(tasks, list) else 0,
        }

    @classmethod
    def _response_summary(cls, body: dict[str, Any]) -> dict[str, Any]:
        data = body.get("data", body)
        result = cls._workflow_result(body)
        return {
            "keys": sorted(data.keys()) if isinstance(data, dict) else [],
            "executionId": data.get("executionId", "") if isinstance(data, dict) else "",
            "status": data.get("status", "") if isinstance(data, dict) else "",
            "resultKeys": sorted(result.keys()) if isinstance(result, dict) else [],
        }

    @staticmethod
    def _workflow_result(body: dict[str, Any]) -> dict[str, Any]:
        data = body.get("data", body)
        if isinstance(data, dict):
            for key in ("result", "output", "response"):
                value = data.get(key)
                if isinstance(value, dict):
                    return value
            nested = data.get("data")
            if isinstance(nested, dict):
                for key in ("result", "output", "response"):
                    value = nested.get(key)
                    if isinstance(value, dict):
                        return value
                return nested
            return data
        return {}

    @staticmethod
    def _response_body(response: httpx.Response) -> dict[str, Any]:
        if not response.content:
            return {}

        try:
            body = response.json()
        except ValueError:
            return {"raw": response.text}

        if isinstance(body, dict):
            return body

        return {"data": body}

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            body = response.text

        if isinstance(body, dict):
            detail = body.get("detail") or body.get("message") or body.get("error")
            if detail:
                return str(detail)

        return f"Fastn returned HTTP {response.status_code}."

    async def resolve_customer_end_org(self, customer_id: str, display_name: str | None = None) -> str:
        body = await self.create_embed_token_for_customer(customer_id, display_name)
        data = body.get("data", body)

        end_org_id = data.get("endOrgId") if isinstance(data, dict) else None

        if not end_org_id:
            raise FastnWorkflowRequestError(
                502,
                "Fastn embed token response did not contain endOrgId.",
            )

        logger.info(
            "fastn.customer_context.resolved customer_id=%s end_org_id=%s",
            customer_id,
            end_org_id,
        )
        return str(end_org_id)
