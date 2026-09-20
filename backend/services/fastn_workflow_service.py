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

    async def execute(self, payload: dict[str, Any], tenant_id: str | None = None) -> dict[str, Any]:
        if not settings.FASTN_API_KEY:
            raise FastnWorkflowConfigurationError("FASTN_API_KEY is not configured.")

        url = f"{self.api_base_url}/api/v1/workflows/{self.workflow_id}/execute"
        headers = {
            "Content-Type": "application/json",
            settings.FASTN_AUTH_HEADER: self._auth_value(),
        }
        if tenant_id:
            headers[settings.FASTN_TENANT_HEADER] = str(tenant_id)
        if settings.FASTN_API_KEY.startswith("fsk_test_"):
            headers["X-fastn-Test-Mode"] = "true"

        logger.info("Executing Fastn workflow %s", self.workflow_id)

        try:
            if self.client is not None:
                response = await self.client.post(url, json={"input": payload}, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=settings.FASTN_TIMEOUT_SECONDS) as client:
                    response = await client.post(url, json={"input": payload}, headers=headers)
        except httpx.HTTPError as exc:
            raise FastnWorkflowRequestError(
                status_code=502,
                detail=f"Fastn workflow request failed: {exc}",
            ) from exc

        if response.status_code >= 400:
            raise FastnWorkflowRequestError(
                status_code=response.status_code,
                detail=self._error_detail(response),
            )

        return self._response_body(response)

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

        try:
            if self.client is not None:
                response = await self.client.post(url, json={}, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=settings.FASTN_TIMEOUT_SECONDS) as client:
                    response = await client.post(url, json={}, headers=headers)
        except httpx.HTTPError as exc:
            raise FastnWorkflowRequestError(502, f"Fastn embed token request failed: {exc}") from exc

        if response.status_code >= 400:
            raise FastnWorkflowRequestError(response.status_code, self._error_detail(response))
        return self._response_body(response)

    async def ensure_customer_org(self, customer_ref: str, display_name: str) -> str:
        """Return the Fastn org id for an app user, creating the end-org once."""
        if not settings.FASTN_API_KEY:
            raise FastnWorkflowConfigurationError("FASTN_API_KEY is not configured.")

        headers = {settings.FASTN_AUTH_HEADER: self._auth_value()}
        if settings.FASTN_API_KEY.startswith("fsk_test_"):
            headers["X-fastn-Test-Mode"] = "true"
        try:
            if self.client is not None:
                response = await self.client.get(f"{self.api_base_url}/api/v1/orgs", headers=headers)
            else:
                async with httpx.AsyncClient(timeout=settings.FASTN_TIMEOUT_SECONDS) as client:
                    response = await client.get(f"{self.api_base_url}/api/v1/orgs", headers=headers)
        except httpx.HTTPError as exc:
            raise FastnWorkflowRequestError(502, f"Fastn organization lookup failed: {exc}") from exc
        if response.status_code >= 400:
            raise FastnWorkflowRequestError(response.status_code, self._error_detail(response))

        organizations = self._response_body(response).get("data", [])
        existing = next((item for item in organizations if item.get("externalRef") == str(customer_ref)), None)
        if existing:
            return str(existing.get("orgId") or existing.get("id"))

        payload = {
            "name": display_name[:200],
            "slug": f"seo-agent-{str(customer_ref).replace('-', '')[:24]}".lower(),
            "external_ref": str(customer_ref),
            "type": "end_org",
            "plan": "free",
        }
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
            raise FastnWorkflowRequestError(502, f"Fastn organization creation failed: {exc}") from exc
        if response.status_code >= 400:
            raise FastnWorkflowRequestError(response.status_code, self._error_detail(response))
        created = self._response_body(response).get("data", {})
        org_id = created.get("orgId") or created.get("id")
        if not org_id:
            raise FastnWorkflowRequestError(502, "Fastn did not return a customer organization id.")
        return str(org_id)

    def _auth_value(self) -> str:
        scheme = settings.FASTN_AUTH_SCHEME.strip()
        if scheme:
            return f"{scheme} {settings.FASTN_API_KEY}"
        return settings.FASTN_API_KEY

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
