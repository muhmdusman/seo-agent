import json
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx

from agents.prompts.seo_review import build_prompt
from services.scraper_service import ScraperService, belongs_to_property, public_address
from services.search_console_service import property_covers_request, verified_property_match
from services.seo_review_service import SEOReviewService, check_page, comparison_windows, summarize_rows
from tools.page_speed_tool import compact_core_web_vitals, summarize_pagespeed_result
from tools.source_html_tool import compact_http_headers, fetch_source_rendering_snapshot, property_home_url


class ReviewTests(unittest.IsolatedAsyncioTestCase):
    def test_completion_does_not_prove_implementation(self):
        self.assertEqual(check_page(None, {"title": "New"})[0], "manual_review")
        self.assertEqual(check_page({"field": "title", "expected": "New"}, {"title": "Old"})[0], "not_observed")
        self.assertEqual(check_page({"field": "title", "expected": "New"}, {"title": "New"})[0], "observed")
        self.assertEqual(check_page({"field": "title", "expected": "New"}, {"fetch_error": "Timeout"})[0], "unavailable")
        self.assertEqual(check_page({"field": "noindex", "expected": "false"}, {"noindex": False})[0], "observed")
        self.assertEqual(check_page({"field": "noindex", "expected": "false"}, {"status_code": 403})[0], "unavailable")

    def test_seven_days_and_reporting_buffer_and_pacific_dates(self):
        completed = "2026-09-01T12:00:00-07:00"
        self.assertIsNone(comparison_windows(completed, datetime.fromisoformat("2026-09-08T12:00:00-07:00")))
        windows = comparison_windows(completed, datetime.fromisoformat("2026-09-11T12:00:00-07:00"))
        self.assertEqual([value.isoformat() for value in windows["before"]], ["2026-08-25", "2026-08-31"])
        self.assertEqual([value.isoformat() for value in windows["after"]], ["2026-09-02", "2026-09-08"])
        # UTC midnight still belongs to the previous reporting day in California.
        self.assertIsNone(comparison_windows(completed, datetime.fromisoformat("2026-09-11T00:00:00+00:00")))

    def test_metrics_are_weighted_and_missing_is_unknown(self):
        self.assertIsNone(summarize_rows({}))
        result = summarize_rows({"rows": [{"clicks": 10, "impressions": 100, "position": 2},
                                            {"clicks": 1, "impressions": 10, "position": 20}]})
        self.assertAlmostEqual(result["ctr"], .1)
        self.assertAlmostEqual(result["position"], 400 / 110)

    async def test_targeted_measurement_and_page_changes_are_independent(self):
        api = AsyncMock()
        api.page_performance.return_value = {"rows": [{"clicks": 2, "impressions": 100, "position": 5}]}
        service = SEOReviewService(api)
        task = {"id": "owned-task", "title": "Update title", "scope": "https://example.com/product",
                "completed_at": "2026-09-01T12:00:00+00:00", "verification": {"field": "title", "expected": "New"}}
        result = await service.review("sc-domain:example.com", {"recent_tasks": [task]},
                                      [{"url": task["scope"], "title": "Old"}], "token",
                                      datetime(2026, 9, 20, tzinfo=timezone.utc))
        self.assertEqual(result[0]["status"], "not_observed")
        self.assertEqual(result[0]["performance"]["status"], "compared")
        self.assertEqual(api.page_performance.await_count, 2)
        self.assertEqual(api.page_performance.await_args_list[0].args[2], task["scope"])

    async def test_missing_and_failed_gsc_do_not_become_success(self):
        api = AsyncMock()
        service = SEOReviewService(api)
        now = datetime(2026, 9, 20, tzinfo=timezone.utc)
        windows = comparison_windows("2026-09-01T12:00:00+00:00", now)
        api.page_performance.return_value = {}
        self.assertEqual((await service._performance("token", "site", "url", windows))["status"], "insufficient_data")
        api.page_performance.side_effect = httpx.ConnectError("unavailable")
        self.assertEqual((await service._performance("token", "site", "url", windows))["status"], "unavailable")

    async def test_measurement_cap_and_future_completion(self):
        api = AsyncMock()
        api.page_performance.return_value = {}
        tasks = [{"id": str(i), "title": "task", "scope": "https://example.com/", "completed_at": "2026-09-01T12:00:00+00:00"} for i in range(6)]
        result = await SEOReviewService(api).review("sc-domain:example.com", {"recent_tasks": tasks}, [], "token", datetime(2026, 9, 20, tzinfo=timezone.utc))
        self.assertEqual(api.page_performance.await_count, 8)
        self.assertEqual(result[-1]["performance"]["status"], "deferred")
        for task, review in zip(tasks, result):
            task["last_measurement_at"] = review["performance"].get("checked_at", "")
        again = await SEOReviewService(api).review("sc-domain:example.com", {"recent_tasks": tasks}, [], "token", datetime(2026, 9, 21, tzinfo=timezone.utc))
        self.assertEqual(again[0]["task_id"], "4")

    def test_prompt_budget_preserves_instructions_and_valid_json(self):
        context = {"property": "https://example.com/", "goal": "qualified leads", "mode": "auto",
                   "pages": [{"url": f"https://example.com/{i}", "text_sample": "long " * 1000} for i in range(20)],
                   "reviews": [], "saved_tasks": [], "competitors": [], "queries": [], "previous_reports": []}
        prompt = build_prompt(context, 5760)
        self.assertLessEqual(len(prompt), 5760)
        data = json.loads(prompt.split("\nINPUT DATA:\n", 1)[1])
        self.assertEqual(data["budget_omissions"]["pages"], 20)
        self.assertIn("Never all 9 stages in one turn", prompt)
        self.assertIn("Only supply this for an observable unmet condition", prompt)
        self.assertEqual(len(context["pages"]), 20)

    def test_minimal_framework_context_fits_demo_budget(self):
        prompt = build_prompt({
            "property": "https://example.com/", "size": "1-10",
            "website_type": "service-based", "goal": "leads", "mode": "auto",
            "phase": "framework",
            "assigned_stages": ["technical-foundation", "crawlability", "rendering", "indexability"],
            "previous_reports": [], "queries": [], "pages": [], "competitors": [],
            "saved_tasks": [], "reviews": [],
        }, 5760)
        self.assertLessEqual(len(prompt), 5760)

    def test_prompt_can_drop_audit_context_under_tiny_budget(self):
        prompt = build_prompt({
            "property": "https://example.com/", "size": "1-10",
            "website_type": "service-based", "goal": "leads", "mode": "auto",
            "phase": "framework",
            "assigned_stages": ["technical-foundation"],
            "previous_reports": [], "queries": [], "pages": [], "competitors": [],
            "saved_tasks": [], "reviews": [],
            "core_web_vitals": {"status": "ok", "strategies": {"mobile": {"lab": {"lcp": {"display_value": "2.2s"}}}}},
            "http_headers": {"headers": {"content-security-policy": "x" * 2000}},
        }, 5760)
        data = json.loads(prompt.split("\nINPUT DATA:\n", 1)[1])
        self.assertIn("http_headers", data["budget_omissions"])

    def test_pagespeed_result_is_normalized_and_compacted(self):
        result = summarize_pagespeed_result({
            "id": "https://example.com/",
            "loadingExperience": {
                "overall_category": "AVERAGE",
                "metrics": {
                    "LARGEST_CONTENTFUL_PAINT_MS": {"percentile": 2800, "category": "AVERAGE"},
                    "CUMULATIVE_LAYOUT_SHIFT_SCORE": {"percentile": 4, "category": "FAST"},
                },
            },
            "lighthouseResult": {
                "requestedUrl": "https://example.com/",
                "finalUrl": "https://example.com/",
                "categories": {"performance": {"score": 0.72}, "seo": {"score": 0.91}},
                "audits": {
                    "largest-contentful-paint": {"numericValue": 3100, "displayValue": "3.1 s", "score": 0.48},
                    "render-blocking-resources": {
                        "title": "Eliminate render-blocking resources",
                        "scoreDisplayMode": "opportunity",
                        "score": 0.4,
                        "displayValue": "Potential savings of 450 ms",
                        "details": {"overallSavingsMs": 450},
                    },
                },
            },
        }, "mobile")
        self.assertEqual(result["scores"]["performance"], 72)
        self.assertEqual(result["scores"]["seo"], 91)
        self.assertEqual(result["field"]["lcp"]["display_value"], "2.8s")
        self.assertEqual(result["field"]["cls"]["value"], 0.04)
        self.assertEqual(result["lab"]["lcp"]["display_value"], "3.1 s")
        self.assertEqual(result["opportunities"][0]["savings_ms"], 450)
        compact = compact_core_web_vitals({"status": "ok", "strategies": {"mobile": result}})
        self.assertNotIn("opportunities", compact["strategies"]["mobile"])
        self.assertEqual(compact["strategies"]["mobile"]["lab"]["lcp"]["value"], 3100)

    def test_property_url_and_header_compaction(self):
        self.assertEqual(property_home_url("sc-domain:example.com"), "https://example.com/")
        self.assertEqual(property_home_url("https://example.com/path/page"), "https://example.com/path/")
        compact = compact_http_headers({
            "status": "ok", "checked_at": "now", "requested_url": "https://example.com/",
            "final_url": "https://example.com/", "status_code": 200, "http_version": "HTTP/2",
            "headers": {"content-type": "text/html", "cache-control": "max-age=0"},
            "redirects": [],
        })
        self.assertEqual(compact["headers"]["content-type"], "text/html")

    async def test_source_rendering_snapshot_is_compact(self):
        html = b"""<html><head><title>Rendered</title><script id="__NEXT_DATA__">{}</script></head>
        <body><main><h1>Hello</h1><p>""" + (b"copy " * 250) + b"""</p><a href="/x">x</a></main></body></html>"""
        with patch("tools.source_html_tool._fetch_limited_source", AsyncMock(return_value={
            "url": "https://example.com/",
            "status_code": 200,
            "headers": httpx.Headers({"content-type": "text/html"}),
            "body": html,
            "truncated": False,
            "redirects": [],
        })):
            result = await fetch_source_rendering_snapshot("https://example.com/")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["rendering_strategy"], "server-rendered-or-prerendered")
        self.assertIn("nextjs", result["framework_hints"])
        self.assertNotIn("body", result)

    def test_search_console_domain_property_covers_url_prefix_request(self):
        sites = {"siteEntry": [
            {"siteUrl": "sc-domain:zocialplug.com", "permissionLevel": "siteOwner"},
            {"siteUrl": "https://unverified.example/", "permissionLevel": "siteUnverifiedUser"},
        ]}
        self.assertTrue(property_covers_request("sc-domain:zocialplug.com", "https://www.zocialplug.com/"))
        self.assertFalse(property_covers_request("sc-domain:zocialplug.com", "https://zocialplug.com.attacker.test/"))
        self.assertEqual(verified_property_match(sites, "https://www.zocialplug.com/"), "sc-domain:zocialplug.com")


class ScraperTests(unittest.IsolatedAsyncioTestCase):
    def test_scope_checks_do_not_accept_similar_hosts(self):
        self.assertTrue(belongs_to_property("https://blog.example.com/page", "sc-domain:example.com"))
        self.assertFalse(belongs_to_property("https://example.com.attacker.test/", "sc-domain:example.com"))
        self.assertFalse(belongs_to_property("https://example.com/private", "https://example.com/public/"))
        self.assertTrue(belongs_to_property("https://example.com", "https://example.com/"))
        self.assertFalse(belongs_to_property("file:///etc/passwd", "sc-domain:example.com"))
        self.assertFalse(belongs_to_property("https://[invalid", "sc-domain:example.com"))

    async def test_private_dns_is_rejected(self):
        with patch("asyncio.get_running_loop") as loop:
            loop.return_value.getaddrinfo = AsyncMock(return_value=[(2, 1, 6, "", ("127.0.0.1", 80))])
            with self.assertRaises(ValueError):
                await public_address("https://example.com/")

    async def test_scraped_html_contains_verifiable_fields(self):
        service = ScraperService()
        service._fetch = AsyncMock(return_value={"url": "https://example.com/", "status_code": 200,
            "headers": {"content-type": "text/html", "x-robots-tag": "noindex"},
            "body": b'<html><head><title>New</title><meta name="viewport" content="width=device-width"><link rel="canonical" href="/canonical"></head><body><h1>Hello</h1></body></html>'})
        page = await service.scrape_page("https://example.com/", "sc-domain:example.com")
        self.assertEqual(page["title"], "New")
        self.assertEqual(page["canonical"], "https://example.com/canonical")
        self.assertTrue(page["noindex"])
        self.assertEqual(page["viewport"], "width=device-width")

    async def test_priority_urls_and_fetch_budget(self):
        service = ScraperService()
        service.scrape_page = AsyncMock(side_effect=lambda url, site: {"url": url})
        pages = await service.scrape_from_sitemap(None, max_pages=2,
            priority_urls=["https://example.com/changed", "https://example.com/second", "https://example.com/third"],
            site_url="sc-domain:example.com")
        self.assertEqual([page["url"] for page in pages], ["https://example.com/changed", "https://example.com/second"])
        self.assertEqual(service.scrape_page.await_count, 2)

    async def test_nested_sitemap_and_off_site_urls(self):
        service = ScraperService()
        service._fetch = AsyncMock(side_effect=[
            {"status_code": 200, "body": b'<sitemapindex><sitemap><loc>https://example.com/pages.xml</loc></sitemap></sitemapindex>'},
            {"status_code": 200, "body": b'<urlset><url><loc>https://example.com/good</loc></url><url><loc>http://127.0.0.1/secret</loc></url></urlset>'},
        ])
        service.scrape_page = AsyncMock(side_effect=lambda url, site: {"url": url})
        pages = await service.scrape_from_sitemap("https://example.com/sitemap.xml", max_pages=3, site_url="sc-domain:example.com")
        self.assertEqual([page["url"] for page in pages], ["https://example.com/", "https://example.com/good"])


if __name__ == "__main__":
    unittest.main()
