"""Server-computed observations and dated measurements; the LLM cannot verify tasks."""
import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx

from services.scraper_service import belongs_to_property
from services.search_console_service import SearchConsoleService

PACIFIC = ZoneInfo("America/Los_Angeles")
FIELDS = ("title", "meta_description", "canonical", "h1", "noindex", "viewport", "status_code")


def check_page(check: dict | None, page: dict | None) -> tuple[str, str]:
    if not page or page.get("fetch_error"):
        return "unavailable", "The affected page could not be checked in this sample."
    if not check:
        return "manual_review", "No machine-checkable acceptance condition is saved; inspect this change manually."
    field, expected = check["field"], check["expected"]
    if field not in page:
        return "unavailable", f"The response did not contain an observable {field} field."
    actual = page[field]
    if isinstance(actual, bool):
        matched = str(actual).lower() == expected.lower()
    elif isinstance(actual, list):
        matched = expected in actual
    else:
        matched = str(actual).strip() == expected.strip()
    return ("observed" if matched else "not_observed",
            f"Saved {field} check {'matched' if matched else 'did not match'} the fetched response. This checks one condition, not the whole task or Google indexing.")


def comparison_windows(completed_at: str, now: datetime):
    changed = datetime.fromisoformat(completed_at).astimezone(PACIFIC).date()
    latest = now.astimezone(PACIFIC).date() - timedelta(days=3)
    # Exclude the completion day; require seven complete post-change days.
    if latest < changed + timedelta(days=7):
        return None
    return {"before": (changed - timedelta(days=7), changed - timedelta(days=1)),
            "after": (latest - timedelta(days=6), latest)}


def summarize_rows(data: dict):
    rows = data.get("rows", [])
    if not rows:
        return None
    impressions = sum(row.get("impressions", 0) for row in rows)
    if impressions <= 0:
        return None
    clicks = sum(row.get("clicks", 0) for row in rows)
    return {"clicks": clicks, "impressions": impressions, "ctr": clicks / impressions,
            "position": sum(row.get("position", 0) * row.get("impressions", 0) for row in rows) / impressions,
            "days_with_data": len(rows)}


class SEOReviewService:
    def __init__(self, search_console=None):
        self.search_console = search_console or SearchConsoleService()

    async def review(self, site_url, history, pages, access_token, now=None, search_console_site_url=None):
        now = now or datetime.now(timezone.utc)
        measurement_site_url = search_console_site_url or site_url
        by_url = {page.get("url"): page for page in pages}
        previous = {page.get("url"): page for page in history.get("previous_pages", [])}
        reviews, measured = [], 0
        for task in sorted(history.get("recent_tasks", []), key=lambda item: (item.get("last_measurement_at", ""), item["id"])):
            page = by_url.get(task["scope"])
            status, detail = check_page(task.get("verification"), page)
            prior = previous.get(task["scope"])
            changed_fields = [field for field in FIELDS if page and prior and field in page and field in prior and page[field] != prior[field]]
            review = {"task_id": task["id"], "title": task["title"], "status": status,
                      "detail": detail, "checked_at": now.isoformat(), "changed_fields": changed_fields,
                      "url": task["scope"], "condition": task.get("verification"),
                      "observed_value": page.get(task["verification"]["field"]) if page and task.get("verification") else None}
            performance = {"status": "not_completed", "detail": "Mark the implementation complete to start a dated performance review."}
            if task.get("completed_at"):
                windows = comparison_windows(task["completed_at"], now)
                if windows is None:
                    performance = {"status": "waiting", "detail": "Waiting for seven full post-completion days plus a three-day reporting buffer."}
                elif not belongs_to_property(task["scope"], site_url):
                    performance = {"status": "manual_review", "detail": "This task needs a single affected property URL for page-level measurement."}
                elif measured >= 4:
                    performance = {"status": "deferred", "detail": "The four-task measurement budget was reached. A later review will check more work."}
                else:
                    measured += 1
                    performance = await self._performance(access_token, measurement_site_url, task["scope"], windows)
                    performance["checked_at"] = now.isoformat()
            review["performance"] = performance
            reviews.append(review)
        return reviews

    async def _performance(self, access_token, site_url, page_url, windows):
        dates = {key: {"start": value[0].isoformat(), "end": value[1].isoformat()} for key, value in windows.items()}
        try:
            before, after = await asyncio.gather(*[
                self.search_console.page_performance(access_token, site_url, page_url, *windows[key])
                for key in ("before", "after")
            ])
            first, last = summarize_rows(before), summarize_rows(after)
            if not first or not last:
                return {"status": "insufficient_data", "windows": dates,
                        "detail": "One comparison window has no usable impressions. Missing rows do not prove zero traffic or an indexing failure."}
            return {"status": "compared", "windows": dates, "before": first, "after": last,
                    "detail": "Observed association only. Completion time is user-reported; demand, seasonality, other changes and Google recrawling can affect these numbers."}
        except (httpx.HTTPError, ValueError):
            return {"status": "unavailable", "windows": dates, "detail": "Search Console comparison was unavailable; no outcome was inferred."}
