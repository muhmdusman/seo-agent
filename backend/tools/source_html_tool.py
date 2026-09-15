"""Raw HTTP header and compact source-rendering evidence for SEO reviews."""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

from services.scraper_service import public_address

USER_AGENT = "SEOReview/1.0"
HEADER_ALLOWLIST = (
    "content-type",
    "cache-control",
    "server",
    "x-robots-tag",
    "strict-transport-security",
    "content-security-policy",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
    "link",
    "location",
    "vary",
    "age",
    "etag",
    "last-modified",
    "cf-cache-status",
    "x-cache",
    "x-vercel-cache",
)


def property_home_url(site_url: str) -> str:
    """Resolve a Search Console property to a public page URL for audits."""
    if site_url.startswith("sc-domain:"):
        return f"https://{site_url.removeprefix('sc-domain:').strip('/')}/"
    parsed = urlsplit(site_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only HTTP(S) Search Console properties can be audited.")
    path = parsed.path or "/"
    if not path.endswith("/"):
        path = path.rsplit("/", 1)[0] + "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def _compact_headers(headers: httpx.Headers) -> dict[str, str]:
    result: dict[str, str] = {}
    for key in HEADER_ALLOWLIST:
        value = headers.get(key)
        if value:
            result[key] = " ".join(value.split())[:600]
    return result


async def _fetch_limited_source(url: str, byte_limit: int = 350_000) -> dict:
    current_url = url
    redirects: list[dict] = []
    async with httpx.AsyncClient(timeout=10, trust_env=False, follow_redirects=False) as client:
        for _ in range(5):
            address = await public_address(current_url)
            original = httpx.URL(current_url)
            async with client.stream(
                "GET",
                original.copy_with(host=address),
                headers={"Host": original.netloc.decode(), "User-Agent": USER_AGENT},
                extensions={"sni_hostname": original.host},
            ) as response:
                if response.status_code in {301, 302, 303, 307, 308} and response.headers.get("location"):
                    next_url = urljoin(current_url, response.headers["location"])
                    redirects.append({"status_code": response.status_code, "location": next_url[:1000]})
                    current_url = next_url
                    continue
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) >= byte_limit:
                        break
                return {
                    "url": current_url,
                    "status_code": response.status_code,
                    "headers": response.headers,
                    "body": bytes(body),
                    "truncated": len(body) >= byte_limit,
                    "redirects": redirects,
                }
    raise ValueError("Redirect limit reached.")


async def fetch_source_rendering_snapshot(site_url: str) -> dict:
    """Return compact source-HTML rendering signals, never full source HTML."""
    checked_at = datetime.now(timezone.utc).isoformat()
    try:
        requested_url = property_home_url(site_url)
        result = await _fetch_limited_source(requested_url)
        headers = result["headers"]
        if "html" not in headers.get("content-type", "").lower():
            return {
                "status": "unavailable",
                "checked_at": checked_at,
                "requested_url": requested_url,
                "final_url": result["url"],
                "status_code": result["status_code"],
                "error": "Response was not HTML.",
            }
        soup = BeautifulSoup(result["body"], "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        body = soup.body or soup
        script_tags = soup.find_all("script")
        inline_json_ids = {str(tag.get("id", "")) for tag in script_tags if tag.get("id")}
        framework_hints = []
        if "__NEXT_DATA__" in inline_json_ids or soup.select_one("script[src*='/_next/']"):
            framework_hints.append("nextjs")
        if "__NUXT_DATA__" in inline_json_ids or soup.select_one("script[src*='/_nuxt/']"):
            framework_hints.append("nuxt")
        if soup.select_one("[data-astro-cid], script[src*='/_astro/']"):
            framework_hints.append("astro")
        root_like = soup.select_one("#root, #app, #__next, [data-reactroot]")
        root_text_chars = len(root_like.get_text(" ", strip=True)) if root_like else None
        text_chars = len(body.get_text(" ", strip=True))
        link_count = len(soup.find_all("a"))
        heading_count = len(soup.find_all(["h1", "h2", "h3"]))
        if text_chars >= 800 and heading_count:
            rendering_strategy = "server-rendered-or-prerendered"
        elif root_like and (root_text_chars or 0) < 120 and len(script_tags) >= 4:
            rendering_strategy = "client-rendered-shell"
        elif text_chars < 300 and len(script_tags) >= 6:
            rendering_strategy = "likely-client-rendered"
        else:
            rendering_strategy = "mixed-or-unknown"
        return {
            "status": "ok",
            "checked_at": checked_at,
            "requested_url": requested_url,
            "final_url": result["url"],
            "status_code": result["status_code"],
            "title_present": bool(title.strip()),
            "body_text_chars": text_chars,
            "root_text_chars": root_text_chars,
            "link_count": link_count,
            "heading_count": heading_count,
            "script_count": len(script_tags),
            "framework_hints": sorted(set(framework_hints)),
            "rendering_strategy": rendering_strategy,
            "truncated": result["truncated"],
        }
    except (httpx.HTTPError, ValueError, OSError) as exc:
        return {
            "status": "unavailable",
            "checked_at": checked_at,
            "requested_url": site_url,
            "error": type(exc).__name__ if not isinstance(exc, ValueError) else str(exc),
        }


async def fetch_http_header_snapshot(site_url: str) -> dict:
    """Fetch response headers for the audited home URL without storing body content."""
    checked_at = datetime.now(timezone.utc).isoformat()
    try:
        requested_url = property_home_url(site_url)
    except ValueError as exc:
        return {
            "status": "unavailable",
            "checked_at": checked_at,
            "requested_url": site_url,
            "error": str(exc),
            "redirects": [],
        }
    current_url = requested_url
    redirects: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=10, trust_env=False, follow_redirects=False) as client:
            for _ in range(5):
                address = await public_address(current_url)
                original = httpx.URL(current_url)
                response = await client.get(
                    original.copy_with(host=address),
                    headers={
                        "Host": original.netloc.decode(),
                        "User-Agent": USER_AGENT,
                        "Range": "bytes=0-8191",
                    },
                    extensions={"sni_hostname": original.host},
                )
                if response.status_code in {301, 302, 303, 307, 308} and response.headers.get("location"):
                    next_url = urljoin(current_url, response.headers["location"])
                    redirects.append({
                        "status_code": response.status_code,
                        "location": next_url[:1000],
                    })
                    current_url = next_url
                    continue
                return {
                    "status": "ok",
                    "checked_at": checked_at,
                    "requested_url": requested_url,
                    "final_url": current_url,
                    "status_code": response.status_code,
                    "http_version": response.http_version,
                    "headers": _compact_headers(response.headers),
                    "redirects": redirects,
                }
        return {
            "status": "unavailable",
            "checked_at": checked_at,
            "requested_url": requested_url,
            "error": "Redirect limit reached.",
            "redirects": redirects,
        }
    except (httpx.HTTPError, ValueError, OSError) as exc:
        return {
            "status": "unavailable",
            "checked_at": checked_at,
            "requested_url": requested_url,
            "error": type(exc).__name__,
            "redirects": redirects,
        }


def compact_http_headers(snapshot: dict | None) -> dict | None:
    """Keep only concise technical signals for display/model context."""
    if not snapshot:
        return None
    return {
        "status": snapshot.get("status"),
        "checked_at": snapshot.get("checked_at"),
        "requested_url": snapshot.get("requested_url"),
        "final_url": snapshot.get("final_url"),
        "status_code": snapshot.get("status_code"),
        "http_version": snapshot.get("http_version"),
        "headers": snapshot.get("headers") or {},
        "redirects": snapshot.get("redirects") or [],
        "error": snapshot.get("error"),
    }
