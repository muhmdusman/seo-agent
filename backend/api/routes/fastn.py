import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from core.config import settings
from dependencies.auth import authenticate
from schemas.fastn import FastnWorkflowExecuteRequest, FastnWorkflowExecuteResponse
from services.fastn_workflow_service import (
    FastnWorkflowConfigurationError,
    FastnWorkflowRequestError,
    FastnWorkflowService,
)
from services.fastn_task_sync_service import FastnTaskSyncService
from models.user import User
from db.dbconfig import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fastn", tags=["fastn"])


async def _fastn_customer_id(user, db: AsyncSession) -> str:
    context = await _fastn_customer_context(user, db)
    return context["endOrgId"]


async def _fastn_customer_context(user, db: AsyncSession) -> dict[str, str]:
    customer_ref = str(user["sub"])
    account = await db.get(User, UUID(customer_ref))
    display_name = f"SEO Agent User {customer_ref[:8]}"
    if account and account.email:
        display_name = f"SEO Agent {account.email}"[:200]
    service = FastnWorkflowService()
    end_org_id = await service.resolve_customer_end_org(customer_ref)
    logger.info(
        "fastn.customer_context app_user_id=%s app_user_email=%s display_name=%s end_org_id=%s",
        customer_ref,
        account.email if account and account.email else "",
        display_name,
        end_org_id,
    )
    return {
        "appUserId": customer_ref,
        "appUserEmail": account.email if account and account.email else "",
        "endOrgId": end_org_id,
    }


@router.post("/reports/{report_id}/sync")
async def sync_report_tasks(
    report_id: UUID,
    user=Depends(authenticate),
    db: AsyncSession = Depends(get_db),
):
    logger.info("fastn.report_sync.route.start report_id=%s app_user_id=%s", report_id, user["sub"])
    try:
        result = await FastnTaskSyncService(db).sync_report(report_id, UUID(user["sub"]))
        logger.info(
            "fastn.report_sync.route.success report_id=%s app_user_id=%s result_keys=%s",
            report_id,
            user["sub"],
            sorted(result.keys()) if isinstance(result, dict) else [],
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FastnWorkflowConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FastnWorkflowRequestError as exc:
        raise HTTPException(status_code=exc.status_code if exc.status_code < 500 else 502,
                            detail=exc.detail) from exc


@router.post("/embed-token")
async def create_embed_token(user=Depends(authenticate), db: AsyncSession = Depends(get_db)):
    logger.info("fastn.embed_token.route.start app_user_id=%s", user["sub"])
    try:
        service = FastnWorkflowService()
        context = await _fastn_customer_context(user, db)
        customer_id = context["endOrgId"]
        result = await service.create_embed_token(customer_id)
    except FastnWorkflowConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FastnWorkflowRequestError as exc:
        raise HTTPException(
            status_code=exc.status_code if exc.status_code < 500 else 502,
            detail=exc.detail,
        ) from exc

    data = result.get("data", result)
    token = data.get("token") if isinstance(data, dict) else None
    if not token:
        logger.error("fastn.embed_token.route.missing_token app_user_id=%s end_org_id=%s", user["sub"], customer_id)
        raise HTTPException(status_code=502, detail="Fastn did not return an embed token.")
    logger.info(
        "fastn.embed_token.route.success app_user_id=%s app_user_email=%s end_org_id=%s returned_end_org_id=%s",
        context["appUserId"],
        context["appUserEmail"],
        customer_id,
        data.get("endOrgId", customer_id),
    )
    return {
        "token": token,
        "endOrgId": data.get("endOrgId", customer_id),
        "expiresIn": data.get("expiresIn", 28800),
        "iframeUrl": f"{settings.FASTN_API_BASE_URL.rstrip('/')}/api/v1/embed/iframe?token={token}",
        "appUser": {
            "id": context["appUserId"],
            "email": context["appUserEmail"],
        },
    }


@router.get("/github/repos")
async def list_github_repositories(user=Depends(authenticate), db: AsyncSession = Depends(get_db)):
    logger.info("fastn.github_repos.route.start app_user_id=%s", user["sub"])
    try:
        customer_id = await _fastn_customer_id(user, db)
        repositories = await FastnWorkflowService().list_github_repositories(customer_id)
    except FastnWorkflowConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FastnWorkflowRequestError as exc:
        raise HTTPException(
            status_code=exc.status_code if exc.status_code < 500 else 502,
            detail=exc.detail,
        ) from exc
    logger.info(
        "fastn.github_repos.route.success app_user_id=%s end_org_id=%s repositories=%s",
        user["sub"],
        customer_id,
        len(repositories),
    )
    return {"repositories": repositories}


@router.get("/google-sheets/spreadsheets")
async def list_google_spreadsheets(user=Depends(authenticate), db: AsyncSession = Depends(get_db)):
    logger.info("fastn.google_sheets.route.start app_user_id=%s", user["sub"])
    try:
        customer_id = await _fastn_customer_id(user, db)
        spreadsheets = await FastnWorkflowService().list_google_spreadsheets(customer_id)
    except FastnWorkflowConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FastnWorkflowRequestError as exc:
        raise HTTPException(
            status_code=exc.status_code if exc.status_code < 500 else 502,
            detail=exc.detail,
        ) from exc
    logger.info(
        "fastn.google_sheets.route.success app_user_id=%s end_org_id=%s spreadsheets=%s",
        user["sub"],
        customer_id,
        len(spreadsheets),
    )
    return {"spreadsheets": spreadsheets}


@router.get("/destinations")
async def list_destinations(user=Depends(authenticate), db: AsyncSession = Depends(get_db)):
    logger.info("fastn.destinations.route.start app_user_id=%s", user["sub"])
    try:
        context = await _fastn_customer_context(user, db)
        customer_id = context["endOrgId"]
        options = await FastnWorkflowService().destination_options(customer_id)
    except FastnWorkflowConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FastnWorkflowRequestError as exc:
        raise HTTPException(
            status_code=exc.status_code if exc.status_code < 500 else 502,
            detail=exc.detail,
        ) from exc
    repositories = options.get("repositories") if isinstance(options.get("repositories"), list) else []
    spreadsheets = options.get("spreadsheets") if isinstance(options.get("spreadsheets"), list) else []
    errors = options.get("errors") if isinstance(options.get("errors"), dict) else {}
    accounts = options.get("accounts") if isinstance(options.get("accounts"), dict) else {}
    logger.info(
        "fastn.destinations.route.success app_user_id=%s app_user_email=%s end_org_id=%s github_login=%s repositories=%s spreadsheets=%s errors=%s",
        context["appUserId"],
        context["appUserEmail"],
        customer_id,
        ((accounts.get("github") or {}).get("login", "")),
        len(repositories),
        len(spreadsheets),
        sorted(errors.keys()),
    )
    return {
        "repositories": repositories,
        "spreadsheets": spreadsheets,
        "errors": errors,
        "accounts": accounts,
        "endOrgId": customer_id,
        "appUser": {
            "id": context["appUserId"],
            "email": context["appUserEmail"],
        },
    }


@router.post(
    "/daily-seo-agent/execute",
    response_model=FastnWorkflowExecuteResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def execute_daily_seo_agent_workflow(
    body: FastnWorkflowExecuteRequest | None = None,
    user=Depends(authenticate),
    db: AsyncSession = Depends(get_db),
):
    logger.info("fastn.daily_execute.route.start app_user_id=%s", user["sub"])
    try:
        customer_id = await _fastn_customer_id(user, db)
        workflow_input = (body or FastnWorkflowExecuteRequest()).workflow_input()
        logger.info(
            "fastn.daily_execute.route.resolved app_user_id=%s end_org_id=%s input_keys=%s site_url=%s",
            user["sub"],
            customer_id,
            sorted(workflow_input.keys()),
            workflow_input.get("siteUrl", ""),
        )
        result = await FastnWorkflowService().execute(
            workflow_input,
            tenant_id=customer_id,
        )
    except FastnWorkflowConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except FastnWorkflowRequestError as exc:
        logger.warning("Fastn workflow execution failed: %s", exc.detail)
        raise HTTPException(
            status_code=exc.status_code if exc.status_code < 500 else status.HTTP_502_BAD_GATEWAY,
            detail=exc.detail,
        ) from exc

    response = FastnWorkflowExecuteResponse(
        workflow_id=settings.FASTN_WORKFLOW_ID,
        status_code=status.HTTP_202_ACCEPTED,
        result=result,
    )
    logger.info(
        "fastn.daily_execute.route.success app_user_id=%s end_org_id=%s workflow_id=%s result_keys=%s",
        user["sub"],
        customer_id,
        settings.FASTN_WORKFLOW_ID,
        sorted(result.keys()) if isinstance(result, dict) else [],
    )

    return response
