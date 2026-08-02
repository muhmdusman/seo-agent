"""
AWS Lambda handler for automated daily SEO report generation.

This handler can be triggered by AWS EventBridge (CloudWatch Events)
on a daily schedule to automatically generate and email SEO reports
to all active users.

Environment Variables Required:
    - All variables from core/config.py (DATABASE_URL, GOOGLE_CLIENT_ID, etc.)
    - WEB3FORMS_ACCESS_KEY
    - SCHEDULER_ENABLED
    - DAILY_REPORT_TIME
    - ADMIN_EMAIL
"""

import asyncio
import json
import logging
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings
from services.scheduler_service import run_daily_reports_job

# Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Create database engine for Lambda
# This will be reused across Lambda invocations (warm starts)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def run_reports() -> Dict[str, Any]:
    """
    Execute the daily reports job.
    
    Returns:
        dict: Statistics about the run
    """
    
    logger.info("Starting Lambda execution for daily reports")
    
    async with AsyncSessionLocal() as session:
        try:
            stats = await run_daily_reports_job(session)
            logger.info(f"Daily reports completed successfully: {stats}")
            return stats
            
        except Exception as e:
            logger.exception("Failed to run daily reports")
            raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler function.
    
    This function is invoked by AWS Lambda when triggered by EventBridge.
    
    Args:
        event: Event data from EventBridge (typically contains schedule info)
        context: Lambda context object with runtime information
        
    Returns:
        dict: Response with status code and execution results
    """
    
    logger.info(f"Lambda invoked with event: {json.dumps(event)}")
    logger.info(f"Request ID: {context.request_id}")
    logger.info(f"Function name: {context.function_name}")
    logger.info(f"Remaining time: {context.get_remaining_time_in_millis()}ms")
    
    try:
        # Check if scheduler is enabled
        if not settings.SCHEDULER_ENABLED:
            logger.warning("Scheduler is disabled in configuration")
            return {
                "statusCode": 503,
                "body": json.dumps({
                    "success": False,
                    "message": "Scheduler is disabled",
                })
            }
        
        # Run the async reports job
        stats = asyncio.run(run_reports())
        
        # Return success response
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "message": "Daily reports completed successfully",
                "statistics": stats,
                "request_id": context.request_id,
            })
        }
        
    except Exception as e:
        logger.exception("Lambda execution failed")
        
        # Return error response
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "message": f"Failed to generate reports: {str(e)}",
                "request_id": context.request_id,
            })
        }


# For local testing
if __name__ == "__main__":
    """
    Test the Lambda handler locally.
    
    Usage:
        python lambda_handler.py
    """
    
    class MockContext:
        """Mock Lambda context for local testing."""
        request_id = "local-test-request-id"
        function_name = "search-console-agent-daily-reports"
        
        @staticmethod
        def get_remaining_time_in_millis():
            return 300000  # 5 minutes
    
    # Mock EventBridge event
    test_event = {
        "version": "0",
        "id": "test-event-id",
        "detail-type": "Scheduled Event",
        "source": "aws.events",
        "time": "2026-08-03T08:00:00Z",
        "region": "us-east-1",
        "resources": ["arn:aws:events:us-east-1:123456789012:rule/daily-seo-reports"],
    }
    
    print("Testing Lambda handler locally...")
    result = lambda_handler(test_event, MockContext())
    print(f"\nResult: {json.dumps(result, indent=2)}")
