from datetime import date

from langchain.tools import tool

from services.search_console_service import SearchConsoleService


search_console_service = SearchConsoleService()


@tool
async def collect_search_console_data(
    access_token: str,
    site_url: str,
    start_date: str,
    end_date: str,
):
    """
    Collect Search Console data for a property.
    """

    return await search_console_service.collect_site_snapshot(
        access_token=access_token,
        site_url=site_url,
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date),
    )