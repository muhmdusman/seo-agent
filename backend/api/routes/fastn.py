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


@router.post("/reports/{report_id}/sync")
async def sync_report_tasks(
    report_id: UUID,
    user=Depends(authenticate),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await FastnTaskSyncService(db).sync_report(report_id, UUID(user["sub"]))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FastnWorkflowConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FastnWorkflowRequestError as exc:
        raise HTTPException(status_code=exc.status_code if exc.status_code < 500 else 502,
                            detail=exc.detail) from exc


@router.post("/embed-token")
async def create_embed_token(user=Depends(authenticate), db: AsyncSession = Depends(get_db)):
    customer_ref = str(user["sub"])
    try:
        account = await db.get(User, UUID(customer_ref))
        display_name = f"SEO Agent User {customer_ref[:8]}"
        if account and account.email:
            display_name = f"SEO Agent {account.email}"[:200]
        service = FastnWorkflowService()
        customer_id = await service.ensure_customer_org(customer_ref, display_name)
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
        raise HTTPException(status_code=502, detail="Fastn did not return an embed token.")
    return {
        "token": token,
        "endOrgId": data.get("endOrgId", customer_id),
        "expiresIn": data.get("expiresIn", 28800),
        "iframeUrl": f"{settings.FASTN_API_BASE_URL.rstrip('/')}/api/v1/embed/iframe?token={token}",
    }


@router.post(
    "/daily-seo-agent/execute",
    response_model=FastnWorkflowExecuteResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def execute_daily_seo_agent_workflow(
    body: FastnWorkflowExecuteRequest | None = None,
    user=Depends(authenticate),
):
    del user

    try:
        result = await FastnWorkflowService().execute(
            (body or FastnWorkflowExecuteRequest()).workflow_input(),
            tenant_id=str(user["sub"]),
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

    return response
