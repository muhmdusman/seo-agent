"""
Daily SEO agent that generates concise reports for automated email delivery.
"""

import logging
from datetime import date, timedelta
from urllib.parse import urljoin

from langchain_mistralai import ChatMistralAI

from core.config import settings
from tools.search_console_tool import collect_search_console_data
from tools.user_context_tool import create_user_context_tool

logger = logging.getLogger(__name__)


class DailyAgent:
    """
    Agent that generates concise daily SEO reports suitable for email delivery.
    Focuses on immediate action items rather than comprehensive analysis.
    """

    def __init__(self, db):
        self.user_tool = create_user_context_tool(db)
        self.llm = ChatMistralAI(
            model_name="mistral-large-latest",
            api_key=settings.MISTRAL_API_KEY,
            temperature=0,
        )

    async def generate_report(
        self,
        user_id: str,
        site_url: str,
    ) -> str:
        """
        Generate a concise daily SEO report.
        
        Args:
            user_id: User UUID
            site_url: Google Search Console property URL
            
        Returns:
            str: Markdown formatted report content
            
        Raises:
            Exception: If report generation fails
        """
        
        try:
            logger.info(
                f"Generating daily report for user={user_id}, site={site_url}"
            )
            
            # Get user credentials
            context = await self.user_tool.ainvoke({"user_id": user_id})
            
            # Fetch last 7 days of Search Console data for daily insights
            snapshot = await collect_search_console_data.ainvoke(
                {
                    "access_token": context["access_token"],
                    "site_url": site_url,
                    "start_date": (date.today() - timedelta(days=7)).isoformat(),
                    "end_date": date.today().isoformat(),
                }
            )
            
            # Generate concise report using LLM
            prompt = self._build_daily_prompt(snapshot, site_url)
            response = await self.llm.ainvoke(prompt)
            
            logger.info(
                f"Daily report generated successfully for user={user_id}, site={site_url}"
            )
            
            return response.content
            
        except Exception as e:
            logger.exception(
                f"Failed to generate daily report for user={user_id}, site={site_url}"
            )
            raise

    def _build_daily_prompt(self, snapshot: dict, site_url: str) -> str:
        """
        Build the LLM prompt for daily report generation.
        
        Args:
            snapshot: Search Console data snapshot
            site_url: Website URL
            
        Returns:
            str: Formatted prompt for the LLM
        """
        
        return f"""
You are an SEO expert analyzing daily Google Search Console data.

**Site:** {site_url}
**Period:** Last 7 days

**Data:**
{snapshot}

**Task:**
Generate a concise daily SEO report suitable for email delivery. Focus on:
1. **Quick Wins** - Immediate opportunities (ready to rank, high impressions/low clicks)
2. **Alerts** - Performance drops, errors, or urgent issues
3. **Today's Focus** - One specific action the user should take today

**Format Requirements:**
- Use GitHub-flavored Markdown
- Start with a brief `##` summary (1-2 sentences) about overall performance
- Use `###` for each section heading
- Keep it concise and actionable (under 500 words)
- Use bullet points for clarity
- Quote queries and URLs with backticks
- Use `**bold**` for metrics and key terms
- NO emoji, NO horizontal rules
- Include specific numbers from the data

**Sections:**

### 📈 Performance Snapshot
- Total clicks, impressions, CTR, average position (compare to previous period)
- Highlight biggest changes (+ or -)

### 🎯 Today's Top Opportunity
- ONE specific query or page to optimize today
- Why it matters (data-backed)
- Quick action to take

### ⚠️ Attention Needed (if any)
- Pages with dropping performance
- Technical issues from Search Console
- Only include if there's something urgent

**Style:**
- Direct and actionable
- Assume the reader has 2 minutes
- Every recommendation must cite specific data
"""

    async def generate_multi_site_report(
        self,
        user_id: str,
        sites: list[str],
    ) -> dict[str, str]:
        """
        Generate reports for multiple sites.
        
        Args:
            user_id: User UUID
            sites: List of site URLs to generate reports for
            
        Returns:
            dict: Mapping of site_url to report content
        """
        
        reports = {}
        
        for site_url in sites:
            try:
                report = await self.generate_report(user_id, site_url)
                reports[site_url] = report
            except Exception as e:
                logger.error(
                    f"Failed to generate report for site {site_url}: {e}"
                )
                # Continue with other sites even if one fails
                reports[site_url] = None
        
        return reports


# Factory function for backward compatibility
def create_daily_agent(db):
    """Create a DailyAgent instance."""
    return DailyAgent(db)
