from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import select

from models.site_settings import SiteSettings


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
        return row or SiteSettings(user_id=user_id, site_url=site_url)

    async def update(self, user_id: UUID, site_url: str, github_repo_url: str) -> SiteSettings:
        owner, repo = parse_github_repo(github_repo_url)
        row = await self.db.scalar(select(SiteSettings).where(
            SiteSettings.user_id == user_id, SiteSettings.site_url == site_url,
        ))
        if row is None:
            row = SiteSettings(user_id=user_id, site_url=site_url)
            self.db.add(row)
        row.github_owner = owner
        row.github_repo = repo
        await self.db.commit()
        await self.db.refresh(row)
        return row
