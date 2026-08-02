"""
Scheduler service for automated daily SEO report generation and delivery.
"""

import logging
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.daily_agent import DailyAgent
from models.user import User
from models.oauth_account import OAuthAccount
from services.email_service import email_service
from services.search_console_service import SearchConsoleService

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Service that orchestrates daily report generation and email delivery
    for all active users with verified Google Search Console properties.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.daily_agent = DailyAgent(db)
        self.search_console_service = SearchConsoleService()

    async def run_daily_reports(self) -> dict:
        """
        Execute daily report generation for all users.
        
        This is the main entry point called by the scheduler (cron/Lambda).
        
        Returns:
            dict: Summary statistics of the run
                {
                    'total_users': int,
                    'successful_users': int,
                    'failed_users': int,
                    'total_sites': int,
                    'successful_reports': int,
                    'failed_reports': int,
                    'errors': list[str]
                }
        """
        
        logger.info("Starting daily report generation run")
        
        stats = {
            'total_users': 0,
            'successful_users': 0,
            'failed_users': 0,
            'total_sites': 0,
            'successful_reports': 0,
            'failed_reports': 0,
            'errors': []
        }
        
        try:
            # Fetch all users with valid OAuth accounts
            users = await self._get_active_users()
            stats['total_users'] = len(users)
            
            if not users:
                logger.warning("No active users found for daily report generation")
                return stats
            
            logger.info(f"Processing daily reports for {len(users)} users")
            
            # Process each user
            for user in users:
                try:
                    user_stats = await self._process_user(user)
                    stats['total_sites'] += user_stats['total_sites']
                    stats['successful_reports'] += user_stats['successful_reports']
                    stats['failed_reports'] += user_stats['failed_reports']
                    
                    if user_stats['failed_reports'] == 0:
                        stats['successful_users'] += 1
                    else:
                        stats['failed_users'] += 1
                        
                except Exception as e:
                    logger.exception(f"Failed to process user {user.id}: {e}")
                    stats['failed_users'] += 1
                    stats['errors'].append(f"User {user.email}: {str(e)}")
            
            logger.info(
                f"Daily report run completed. "
                f"Processed {stats['successful_reports']}/{stats['total_sites']} sites "
                f"for {stats['successful_users']}/{stats['total_users']} users"
            )
            
            # Send admin summary if there were errors
            if stats['errors']:
                await self._send_admin_summary(stats)
            
            return stats
            
        except Exception as e:
            logger.exception("Critical error during daily report run")
            stats['errors'].append(f"Critical error: {str(e)}")
            await email_service.send_error_notification(
                error_message=f"Daily report run failed: {str(e)}"
            )
            raise

    async def _get_active_users(self) -> list[User]:
        """
        Fetch all users with valid OAuth credentials.
        
        Returns:
            list[User]: List of active users
        """
        
        from models.oauth_credential import OAuthCredential
        
        query = (
            select(User)
            .join(OAuthAccount, User.id == OAuthAccount.user_id)
            .join(OAuthCredential, OAuthAccount.id == OAuthCredential.oauth_account_id)
            .where(OAuthCredential.access_token.isnot(None))
            .distinct()
        )
        
        result = await self.db.execute(query)
        users = result.scalars().all()
        
        return list(users)

    async def _process_user(self, user: User) -> dict:
        """
        Process daily reports for a single user across all their sites.
        
        Args:
            user: User model instance
            
        Returns:
            dict: Processing statistics for this user
        """
        
        logger.info(f"Processing daily reports for user: {user.email}")
        
        stats = {
            'total_sites': 0,
            'successful_reports': 0,
            'failed_reports': 0,
        }
        
        try:
            # Get user's OAuth account
            oauth_account = await self._get_user_oauth_account(user.id)
            
            if not oauth_account:
                logger.warning(f"No OAuth account found for user {user.email}")
                return stats
            
            # Fetch user's verified sites from Search Console
            sites = await self._get_user_sites(oauth_account.credentials.access_token)
            stats['total_sites'] = len(sites)
            
            if not sites:
                logger.info(f"No verified sites found for user {user.email}")
                return stats
            
            logger.info(
                f"Found {len(sites)} verified sites for user {user.email}"
            )
            
            # Generate and send reports for each site
            for site_url in sites:
                try:
                    await self._generate_and_send_report(
                        user=user,
                        site_url=site_url,
                    )
                    stats['successful_reports'] += 1
                    
                except Exception as e:
                    logger.exception(
                        f"Failed to generate report for site {site_url}: {e}"
                    )
                    stats['failed_reports'] += 1
                    
                    # Send error notification for this specific site
                    await email_service.send_error_notification(
                        error_message=str(e),
                        user_email=user.email,
                        site_url=site_url,
                    )
            
            return stats
            
        except Exception as e:
            logger.exception(f"Error processing user {user.email}: {e}")
            stats['failed_reports'] = stats['total_sites']
            raise

    async def _get_user_oauth_account(self, user_id: str) -> Optional[OAuthAccount]:
        """
        Get the OAuth account with credentials for a user.
        
        Args:
            user_id: User UUID
            
        Returns:
            OAuthAccount or None
        """
        
        from sqlalchemy.orm import selectinload
        
        query = (
            select(OAuthAccount)
            .options(selectinload(OAuthAccount.credentials))
            .where(OAuthAccount.user_id == user_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_user_sites(self, access_token: str) -> list[str]:
        """
        Fetch verified sites from Google Search Console.
        
        Args:
            access_token: Google OAuth access token
            
        Returns:
            list[str]: List of verified site URLs
        """
        
        try:
            sites_data = await self.search_console_service.list_sites(
                access_token
            )
            
            # Extract URLs from the response
            sites = []
            for entry in sites_data.get("siteEntry", []):
                permission = entry.get("permissionLevel", "")
                if permission in ["siteOwner", "siteFullUser"]:
                    sites.append(entry.get("siteUrl"))
            
            return [s for s in sites if s]  # Filter out None values
            
        except Exception as e:
            logger.exception(f"Failed to fetch sites from Search Console: {e}")
            return []

    async def _generate_and_send_report(
        self,
        user: User,
        site_url: str,
    ) -> None:
        """
        Generate a daily report and send it via email.
        
        Args:
            user: User model instance
            site_url: Site URL to generate report for
            
        Raises:
            Exception: If report generation or sending fails
        """
        
        logger.info(
            f"Generating daily report for {user.email} - {site_url}"
        )
        
        # Generate the report
        report_content = await self.daily_agent.generate_report(
            user_id=str(user.id),
            site_url=site_url,
        )
        
        # Send via email
        success = await email_service.send_daily_report(
            user_email=user.email,
            user_name=user.username or user.email.split('@')[0],
            site_url=site_url,
            report_content=report_content,
            report_date=date.today().strftime("%B %d, %Y"),
        )
        
        if not success:
            raise Exception(f"Failed to send email to {user.email}")
        
        logger.info(
            f"Daily report sent successfully to {user.email} for {site_url}"
        )

    async def _send_admin_summary(self, stats: dict) -> None:
        """
        Send a summary email to admin about the daily run.
        
        Args:
            stats: Run statistics dictionary
        """
        
        error_list = "\n".join(stats['errors']) if stats['errors'] else "None"
        
        message = f"""
Daily Report Run Summary
========================

Total Users: {stats['total_users']}
Successful Users: {stats['successful_users']}
Failed Users: {stats['failed_users']}

Total Sites: {stats['total_sites']}
Successful Reports: {stats['successful_reports']}
Failed Reports: {stats['failed_reports']}

Errors:
{error_list}
"""
        
        await email_service.send_error_notification(
            error_message=message
        )


# Convenience function for external use
async def run_daily_reports_job(db: AsyncSession) -> dict:
    """
    Convenience function to run daily reports.
    
    Args:
        db: Database session
        
    Returns:
        dict: Run statistics
    """
    service = SchedulerService(db)
    return await service.run_daily_reports()
