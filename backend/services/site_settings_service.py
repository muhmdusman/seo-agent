import logging
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import select

from models.site_settings import SiteSettings
from schemas.site_settings import SiteSettingsUpdate

logger = logging.getLogger(__name__)


GITHUB_TASK_TERMS = (
    "metadata", "meta description", "title tag", "canonical", "viewport",
    "robots.txt", "sitemap", "schema", "structured data", "json-ld",
    "hreflang", "html", "css", "javascript", " js ", "component", "template",
    "code", "repository", "commit", "deploy", "ssr", "server-side rendering",
    "rendering", "redirect", "http header", "performance", "lcp", "cls", "inp",
    "landing page", "page copy", "content page", "keyword",
)


def is_github_task(task) -> bool:
    values = []
    for field in ("title", "scope", "evidence", "why_it_matters", "manual_fix", "agent_prompt"):
        value = task.get(field, "") if isinstance(task, dict) else getattr(task, field, "")
        values.append(str(value or "").lower())
    text = " ".join(values)
    return any(term in text for term in GITHUB_TASK_TERMS)


def resolved_target_platform(task, repo_configured: bool) -> str:
    current = task.get("target_platform", "manual_review") if isinstance(task, dict) else getattr(task, "target_platform", "manual_review")
    if repo_configured and current in {"manual_review", "google_sheets"} and is_github_task(task):
        return "github"
    return current


def parse_github_repo(value: str) -> tuple[str, str]:
    raw = value.strip().rstrip("/")
    if not raw:
        return "", ""
    if raw.startswith("git@github.com:"):
        path = raw.removeprefix("git@github.com:")
    else:
        parsed = urlsplit(raw if "://" in raw else f"https://github.com/{raw}")
        if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
            raise ValueError("Enter a github.com repository URL.")
        path = parsed.path.strip("/")
    parts = [part for part in path.split("/") if part]
    if len(parts) != 2 or not all(parts):
        raise ValueError("Enter a repository URL like https://github.com/owner/repository.")
    return parts[0], parts[1].removesuffix(".git")


class SiteSettingsService:
    def __init__(self, db):
        self.db = db

    async def get(self, user_id: UUID, site_url: str) -> SiteSettings:
        row = await self.db.scalar(select(SiteSettings).where(
            SiteSettings.user_id == user_id, SiteSettings.site_url == site_url,
        ))
        logger.info(
            "site_settings.get user_id=%s site_url=%s found=%s repo=%s/%s spreadsheet_id=%s",
            user_id,
            site_url,
            bool(row),
            row.github_owner if row else "",
            row.github_repo if row else "",
            row.google_spreadsheet_id if row else "",
        )
        return row or SiteSettings(user_id=user_id, site_url=site_url)

    async def update(self, user_id: UUID, site_url: str, body: SiteSettingsUpdate | str) -> SiteSettings:
        if isinstance(body, str):
            owner, repo = parse_github_repo(body)
            spreadsheet_id = ""
            spreadsheet_name = ""
        elif body.github_owner or body.github_repo:
            owner = body.github_owner.strip()
            repo = body.github_repo.strip()
            if bool(owner) != bool(repo):
                raise ValueError("Select a complete GitHub repository.")
            spreadsheet_id = body.google_spreadsheet_id.strip()
            spreadsheet_name = body.google_spreadsheet_name.strip()
        else:
            owner, repo = parse_github_repo(body.github_repo_url)
            spreadsheet_id = body.google_spreadsheet_id.strip()
            spreadsheet_name = body.google_spreadsheet_name.strip()

        row = await self.db.scalar(select(SiteSettings).where(
            SiteSettings.user_id == user_id, SiteSettings.site_url == site_url,
        ))
        if row is None:
            row = SiteSettings(user_id=user_id, site_url=site_url)
            self.db.add(row)
            logger.info("site_settings.update.create user_id=%s site_url=%s", user_id, site_url)
        row.github_owner = owner
        row.github_repo = repo
        row.google_spreadsheet_id = spreadsheet_id
        row.google_spreadsheet_name = spreadsheet_name
        await self.db.commit()
        await self.db.refresh(row)
        logger.info(
            "site_settings.update.success user_id=%s site_url=%s repo=%s/%s spreadsheet_id=%s spreadsheet_name=%s",
            user_id,
            site_url,
            owner,
            repo,
            spreadsheet_id,
            spreadsheet_name,
        )
        return row
