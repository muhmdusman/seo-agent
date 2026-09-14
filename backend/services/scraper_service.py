"""Bounded public-page sampling; raw HTML observations, not a browser audit."""
import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup
from lxml import etree


def belongs_to_property(url: str, site: str) -> bool:
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            return False
        if site.startswith("sc-domain:"):
            domain = site.removeprefix("sc-domain:").lower()
            return parsed.hostname == domain or parsed.hostname.endswith("." + domain)
        root = urlsplit(site)
        return (parsed.scheme, parsed.hostname, parsed.port) == (root.scheme, root.hostname, root.port) and parsed.path.startswith(root.path)
    except ValueError:
        return False


async def public_address(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 80, 443):
        raise ValueError("Only public HTTP(S) pages on standard ports can be fetched.")
    addresses = await asyncio.get_running_loop().getaddrinfo(
        parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM,
    )
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("Private or reserved network addresses cannot be fetched.")
    return addresses[0][4][0]


class ScraperService:
    async def _fetch(self, url: str, site: str) -> dict:
        for _ in range(4):
            if not belongs_to_property(url, site):
                raise ValueError("URL is outside the requested property.")
            address = await public_address(url)
            original = httpx.URL(url)
            # Pin the validated DNS result, preserving Host and TLS identity.
            # A fresh client avoids sharing TLS connections between virtual hosts.
            async with httpx.AsyncClient(timeout=8, trust_env=False, follow_redirects=False) as client:
                async with client.stream("GET", original.copy_with(host=address),
                                         headers={"Host": original.netloc.decode(), "User-Agent": "SEOReview/1.0"},
                                         extensions={"sni_hostname": original.host}) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        url = urljoin(url, response.headers.get("location", ""))
                        continue
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > 2_000_000:
                            raise ValueError("Page exceeds the 2 MB fetch limit.")
                    return {"url": url, "status_code": response.status_code,
                            "headers": dict(response.headers), "body": bytes(body)}
        raise ValueError("Redirect limit reached.")

    async def scrape_page(self, url: str, site: str) -> dict:
        try:
            result = await self._fetch(url, site)
            base = {"url": url, "final_url": result["url"], "status_code": result["status_code"]}
            if result["status_code"] != 200:
                return base
            if "html" not in result["headers"].get("content-type", "").lower():
                return {**base, "fetch_error": "Response was not HTML."}
            soup = BeautifulSoup(result["body"], "html.parser")
            def meta(name):
                tag = soup.find("meta", attrs={"name": name})
                return str(tag.get("content", "")) if tag else ""
            canonical = soup.find("link", rel="canonical")
            robots = meta("robots") + "," + meta("googlebot") + "," + result["headers"].get("x-robots-tag", "")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            return {**base, "title": soup.title.get_text(" ", strip=True)[:500] if soup.title else "",
                    "meta_description": meta("description")[:1000],
                    "canonical": urljoin(result["url"], canonical["href"]) if canonical and canonical.get("href", "").strip() else "",
                    "h1": [h.get_text(" ", strip=True)[:500] for h in soup.find_all("h1")[:5]],
                    "h2": [h.get_text(" ", strip=True)[:200] for h in soup.find_all("h2")[:8]],
                    "noindex": any(token in robots.lower().replace(",", " ").split() for token in ("noindex", "none")),
                    "viewport": meta("viewport")[:500], "text_sample": soup.get_text(" ", strip=True)[:3000]}
        except (httpx.HTTPError, ValueError, OSError) as exc:
            return {"url": url, "fetch_error": type(exc).__name__}

    async def scrape_from_sitemap(self, sitemap_url: str | None, max_pages: int = 12,
                                  priority_urls: list[str] | None = None, site_url: str | None = None) -> list[dict]:
        site = site_url or (f"{urlsplit(sitemap_url).scheme}://{urlsplit(sitemap_url).netloc}/" if sitemap_url else "")
        urls = list(dict.fromkeys(url for url in (priority_urls or []) if belongs_to_property(url, site)))[:max_pages]
        root_url = "https://" + site.removeprefix("sc-domain:") + "/" if site.startswith("sc-domain:") else site
        if root_url and root_url not in urls and len(urls) < max_pages:
            urls.append(root_url)
        maps, visited = ([sitemap_url] if sitemap_url else []), set()
        pages = []
        try:
            async with asyncio.timeout(45):
                while maps and len(visited) < 3 and len(urls) < max_pages:
                    current = maps.pop(0)
                    if current in visited:
                        continue
                    visited.add(current)
                    try:
                        result = await self._fetch(current, site)
                        if result["status_code"] != 200:
                            continue
                        root = etree.fromstring(result["body"], parser=etree.XMLParser(resolve_entities=False, no_network=True))
                        locations = root.xpath("//*[local-name()='loc']/text()")[:max_pages * 2]
                        if etree.QName(root).localname == "sitemapindex":
                            maps.extend(locations[:3])
                        else:
                            for url in locations:
                                if belongs_to_property(url, site) and url not in urls and len(urls) < max_pages:
                                    urls.append(url)
                    except (httpx.HTTPError, ValueError, OSError, etree.XMLSyntaxError):
                        continue
                for url in urls:
                    pages.append(await self.scrape_page(url, site))
        except TimeoutError:
            pages.append({"fetch_error": "Sampling deadline reached; some pages were not checked."})
        return pages
