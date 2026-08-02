"""
Email service using SMTP for sending daily SEO reports.
Supports Gmail, AWS SES, and any SMTP server.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from jinja2 import Template

from core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP."""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME
        
    async def send_daily_report(
        self,
        user_email: str,
        user_name: str,
        site_url: str,
        report_content: str,
        report_date: str,
    ) -> bool:
        """
        Send a daily SEO report to a user.
        
        Args:
            user_email: Recipient email address
            user_name: Recipient name
            site_url: Website URL being reported on
            report_content: Markdown/HTML formatted report content
            report_date: Date of the report (ISO format)
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        
        subject = f"Daily SEO Report for {site_url} - {report_date}"
        
        html_body = self._format_report_html(
            user_name=user_name,
            site_url=site_url,
            report_content=report_content,
            report_date=report_date,
        )
        
        return await self._send_email(
            to_email=user_email,
            subject=subject,
            html_body=html_body,
        )
    
    async def send_error_notification(
        self,
        error_message: str,
        user_email: Optional[str] = None,
        site_url: Optional[str] = None,
    ) -> bool:
        """
        Send an error notification email.
        
        Args:
            error_message: Description of the error
            user_email: Optional user email (if specific to a user)
            site_url: Optional site URL (if specific to a site)
            
        Returns:
            bool: True if email was sent successfully
        """
        
        recipient = user_email or settings.ADMIN_EMAIL
        subject = "Search Console Agent - Report Generation Failed"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #dc2626;">⚠️ Report Generation Error</h2>
                <p><strong>Error Message:</strong></p>
                <pre style="background: #f3f4f6; padding: 15px; border-radius: 5px; overflow-x: auto;">
{error_message}
                </pre>
                {f'<p><strong>Site URL:</strong> {site_url}</p>' if site_url else ''}
                {f'<p><strong>User Email:</strong> {user_email}</p>' if user_email else ''}
                <p style="margin-top: 20px; font-size: 14px; color: #6b7280;">
                    This is an automated notification from Search Console Agent.
                </p>
            </div>
        </body>
        </html>
        """
        
        return await self._send_email(
            to_email=recipient,
            subject=subject,
            html_body=html_body,
        )
    
    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
    ) -> bool:
        """
        Send an email using SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_body: HTML email body
            
        Returns:
            bool: True if successful, False otherwise
        """
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            
            # Attach HTML body
            html_part = MIMEText(html_body, "html")
            message.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()  # Upgrade to secure connection
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)
            
            logger.info(f"Email sent successfully to {to_email}: {subject}")
            return True
                    
        except Exception as e:
            logger.exception(f"Exception while sending email to {to_email}: {e}")
            return False
    
    def _format_report_html(
        self,
        user_name: str,
        site_url: str,
        report_content: str,
        report_date: str,
    ) -> str:
        """
        Format the SEO report as HTML email.
        
        Args:
            user_name: Recipient name
            site_url: Website URL
            report_content: Report content (markdown formatted)
            report_date: Report date
            
        Returns:
            str: HTML formatted email body
        """
        
        # Convert markdown-style formatting to HTML
        # This is a simple conversion; for production, consider using markdown library
        html_content = report_content.replace("\n", "<br>")
        html_content = self._convert_markdown_to_html(html_content)
        
        template = Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily SEO Report</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f9fafb;">
    <div style="max-width: 700px; margin: 0 auto; background-color: #ffffff;">
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center;">
            <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 700;">
                📊 Daily SEO Report
            </h1>
            <p style="color: #e0e7ff; margin: 10px 0 0 0; font-size: 16px;">
                {{ report_date }}
            </p>
        </div>
        
        <!-- Body -->
        <div style="padding: 40px 30px;">
            <p style="font-size: 16px; color: #374151; margin-bottom: 20px;">
                Hi <strong>{{ user_name }}</strong>,
            </p>
            
            <p style="font-size: 16px; color: #374151; margin-bottom: 30px;">
                Here's your automated daily SEO analysis for 
                <strong style="color: #667eea;">{{ site_url }}</strong>
            </p>
            
            <!-- Report Content -->
            <div style="background-color: #f9fafb; border-left: 4px solid #667eea; padding: 25px; border-radius: 8px; margin-bottom: 30px;">
                <div style="font-size: 15px; line-height: 1.8; color: #1f2937;">
                    {{ report_content | safe }}
                </div>
            </div>
            
            <!-- CTA Button -->
            <div style="text-align: center; margin: 40px 0;">
                <a href="{{ frontend_url }}" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 6px rgba(102, 126, 234, 0.25);">
                    View Full Dashboard
                </a>
            </div>
            
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
            
            <p style="font-size: 14px; color: #6b7280; margin-bottom: 10px;">
                💡 <strong>Tip:</strong> These insights are generated by AI analyzing your Google Search Console data.
            </p>
            
            <p style="font-size: 14px; color: #6b7280;">
                <strong>Questions or feedback?</strong> Reply to this email or visit our dashboard to manage your settings.
            </p>
        </div>
        
        <!-- Footer -->
        <div style="background-color: #f9fafb; padding: 30px; text-align: center; border-top: 1px solid #e5e7eb;">
            <p style="font-size: 13px; color: #9ca3af; margin: 0 0 10px 0;">
                You're receiving this because you enabled daily reports in {{ app_name }}.
            </p>
            <p style="font-size: 13px; color: #9ca3af; margin: 0;">
                <a href="{{ frontend_url }}/settings" style="color: #667eea; text-decoration: none;">Manage Email Preferences</a>
            </p>
        </div>
    </div>
</body>
</html>
        """)
        
        return template.render(
            user_name=user_name,
            site_url=site_url,
            report_content=html_content,
            report_date=report_date,
            frontend_url=settings.FRONTEND_URL,
            app_name=settings.APP_NAME,
        )
    
    def _convert_markdown_to_html(self, text: str) -> str:
        """
        Simple markdown to HTML conversion for email formatting.
        
        Args:
            text: Markdown formatted text
            
        Returns:
            str: HTML formatted text
        """
        
        import re
        
        # Headers
        text = re.sub(r'###\s+(.+?)<br>', r'<h3 style="color: #1f2937; font-size: 18px; margin: 25px 0 15px 0; font-weight: 600;">\1</h3>', text)
        text = re.sub(r'##\s+(.+?)<br>', r'<h2 style="color: #111827; font-size: 22px; margin: 30px 0 20px 0; font-weight: 700;">\1</h2>', text)
        
        # Bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong style="color: #374151;">\1</strong>', text)
        
        # Code/Inline code
        text = re.sub(r'`(.+?)`', r'<code style="background-color: #f3f4f6; padding: 2px 6px; border-radius: 3px; font-family: monospace; font-size: 14px; color: #dc2626;">\1</code>', text)
        
        # Bullet points (simple version)
        text = re.sub(r'^- (.+?)<br>', r'<li style="margin: 8px 0; color: #4b5563;">\1</li>', text, flags=re.MULTILINE)
        text = re.sub(r'(<li.*?</li>)', r'<ul style="margin: 15px 0; padding-left: 25px;">\1</ul>', text)
        
        return text


# Singleton instance
email_service = EmailService()
