"""
API routes for the daily scheduler service.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.dbconfig import get_db
from services.scheduler_service import run_daily_reports_job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.post("/trigger", status_code=status.HTTP_200_OK)
async def trigger_daily_reports(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Manually trigger the daily report generation and email delivery.
    
    This endpoint can be called:
    - Manually for testing
    - By AWS EventBridge/CloudWatch Events
    - By any external cron service
    
    **Note:** In production, this should be protected with authentication
    or API key validation to prevent unauthorized triggers.
    
    Returns:
        dict: Statistics about the run including success/failure counts
    """
    
    if not settings.SCHEDULER_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler is disabled in configuration"
        )
    
    logger.info("Manual trigger received for daily reports")
    
    try:
        stats = await run_daily_reports_job(db)
        
        return {
            "success": True,
            "message": "Daily reports completed",
            "statistics": stats,
        }
        
    except Exception as e:
        logger.exception("Failed to execute daily reports")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}"
        )


@router.get("/status")
async def get_scheduler_status():
    """
    Get the current status of the scheduler service.
    
    Returns:
        dict: Scheduler configuration and status
    """
    
    return {
        "enabled": settings.SCHEDULER_ENABLED,
        "scheduled_time": settings.DAILY_REPORT_TIME,
        "admin_email": settings.ADMIN_EMAIL,
        "service": "operational",
    }


@router.post("/test-email")
async def test_email_service():
    """
    Test the email service by sending a test email to admin.
    
    This is useful for verifying Web3Forms configuration.
    
    Returns:
        dict: Success status and message
    """
    
    from services.email_service import email_service
    from datetime import date
    
    test_report = """
## Test Report

This is a test email from Search Console Agent to verify the email service is working correctly.

### ✅ Email Service Status
- **Web3Forms Integration:** Active
- **Test Date:** {date}
- **Configuration:** Valid

If you're reading this, the email service is working perfectly!
    """.format(date=date.today().strftime("%B %d, %Y"))
    
    try:
        success = await email_service.send_daily_report(
            user_email=settings.ADMIN_EMAIL,
            user_name="Admin",
            site_url="https://example.com",
            report_content=test_report,
            report_date=date.today().strftime("%B %d, %Y"),
        )
        
        if success:
            return {
                "success": True,
                "message": f"Test email sent to {settings.ADMIN_EMAIL}",
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send test email"
            )
            
    except Exception as e:
        logger.exception("Test email failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test email failed: {str(e)}"
        )
