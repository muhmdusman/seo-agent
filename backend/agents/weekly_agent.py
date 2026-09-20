"""One bounded, user-started review: observe, measure, recommend and save."""
import asyncio
import json
import logging
from uuid import UUID
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo
from sqlalchemy import select

from strands import Agent
from strands.models.litellm import LiteLLMModel
from pydantic import ValidationError

from agents.output.seo_review import (
    AnalysisOutputError, INVALID_OUTPUT_MESSAGE, REPAIR_TIMEOUT_SECONDS,
    analysis_response_format, formatting_prompt,
)
from agents.coding_agent import CodingAgent
from agents.prompts.seo_review import build_prompt
from core.config import settings
from core.seo_framework import SEO_STAGES
from schemas.seo import AnalysisDraft
from services.scraper_service import ScraperService
from services.seo_review_service import SEOReviewService
from services.seo_task_generation_service import build_fallback_tasks
from services.fastn_task_sync_service import FastnTaskSyncService
from models.user import User
from services.email_service import email_service
from services.seo_workspace_service import SEOWorkspaceService
from tools.page_speed_tool import compact_core_web_vitals, fetch_core_web_vitals
from tools.search_console_tool import collect_search_console_data
from tools.source_html_tool import compact_http_headers, fetch_http_header_snapshot, fetch_source_rendering_snapshot
from tools.user_context_tool import create_user_context_tool

logger = logging.getLogger(__name__)
STATUS_COMPLETED = "Completed."
STATUS_FAILED = "Failed."


class WeeklyAgent:
    def __init__(self, db):
        self.db = db
        self.workspace_service = SEOWorkspaceService(db)
        self.user_tool = create_user_context_tool(db)
        self.scraper = ScraperService()
        self.reviewer = SEOReviewService()
        self.model = LiteLLMModel(
            model_id=settings.LLM_MODEL_ID,
            stream=False,
            client_args={"api_key": settings.LLM_API_KEY, "num_retries": 0},
            params={"temperature": 0, "max_tokens": 3000 if settings.SEO_DEMO_MODE else 8192,
                    "response_format": analysis_response_format(),
                    "reasoning_effort": "low" if settings.SEO_DEMO_MODE else "medium"},
        )

    @staticmethod
    def _resolve_sitemap_url(snapshot, site_url):
        entries = snapshot.get("sitemaps", {}).get("sitemap", [])
        for entry in entries:
            if entry.get("path"):
                return entry["path"]
        base = "https://" + site_url.removeprefix("sc-domain:") if site_url.startswith("sc-domain:") else site_url
        return urljoin(base, "/sitemap.xml")

    @staticmethod
    def _extract_analysis(response_content):
        text = response_content.strip()
        if text.startswith("```") and text.endswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return AnalysisDraft.model_validate_json(text)

    @staticmethod
    def _normalize_audit_snapshot(snapshot):
        if not snapshot:
            return None
        context = snapshot.get("compact_context") if isinstance(snapshot.get("compact_context"), dict) else snapshot
        core = context.get("core_web_vitals") if isinstance(context, dict) else None
        headers = context.get("http_headers") if isinstance(context, dict) else None
        return {
            "core_web_vitals": compact_core_web_vitals(core) if core and any(
                "opportunities" in data for data in (core.get("strategies") or {}).values()
            ) else core,
            "http_headers": compact_http_headers(headers) if headers and "headers" in headers else headers,
        }

    async def _audit_context(self, site_url, audit_snapshot):
        supplied = self._normalize_audit_snapshot(audit_snapshot)
        if supplied and (supplied.get("core_web_vitals") or supplied.get("http_headers")):
            return supplied
        core_web_vitals, http_headers = await asyncio.gather(
            fetch_core_web_vitals(site_url),
            fetch_http_header_snapshot(site_url),
        )
        return {
            "core_web_vitals": compact_core_web_vitals(core_web_vitals),
            "http_headers": compact_http_headers(http_headers),
        }

    @staticmethod
    def _needs_source_rendering_snapshot(stages, pages):
        if "rendering" in (stages or []):
            return True
        return any(
            page.get("status_code") == 200 and len(page.get("text_sample", "")) < 300
            for page in pages[:3]
        )

    async def _validated_analysis(self, prompt):
        # Fresh agents avoid replaying evidence/history during a formatting-only retry.
        agent = Agent(model=self.model, tools=[], callback_handler=None, retry_strategy=None)
        candidate = str(await agent.invoke_async(prompt))
        try:
            return self._extract_analysis(candidate)
        except ValidationError as error:
            logger.warning("SEO output validation failed; trying one formatting repair")
            repair_prompt = formatting_prompt(candidate, error)
        repair_agent = Agent(model=self.model, tools=[], callback_handler=None, retry_strategy=None)
        try:
            async with asyncio.timeout(REPAIR_TIMEOUT_SECONDS):
                repaired = str(await repair_agent.invoke_async(repair_prompt))
            return self._extract_analysis(repaired)
        except ValidationError:
            raise AnalysisOutputError(INVALID_OUTPUT_MESSAGE) from None
        except TimeoutError:
            raise AnalysisOutputError("The report formatting retry timed out. Your saved report and tasks are unchanged.") from None

    async def _complete_post_save_handoff(self, report_id: UUID, user_id: UUID) -> tuple[dict, object | None]:
        coding_result = {"status": "disabled", "attempted": 0, "proposed": 0, "blocked": 0, "failed": 0}
        if settings.CODING_AGENT_ENABLED:
            try:
                coding_result = await CodingAgent(self.db).propose_report_tasks(report_id, user_id)
            except Exception:
                coding_result = {"status": "failed", "attempted": 0, "proposed": 0, "blocked": 0, "failed": 0}
                logger.exception("Coding-agent report handoff failed for report %s", report_id)

        fastn_result = None
        try:
            fastn_result = await FastnTaskSyncService(self.db).sync_report(report_id, user_id)
        except Exception:
            logger.exception("Fastn task handoff failed for report %s", report_id)
        return coding_result, fastn_result

    async def run(self, user_id, site_url, website_number_of_pages, website_type, user_goal,
                  run_id, mode="auto", focus="", competitor_urls=None,
                  stages=None, phase="framework", audit_snapshot=None, search_console_site_url=None):
        try:
            gsc_site_url = search_console_site_url or site_url
            history = await self.workspace_service.agent_context(user_id, site_url)
            await self.db.rollback()
            yield "Getting Google credentials..."
            credentials = await self.user_tool(user_id=user_id)
            await self.db.rollback()

            yield "Fetching recent Search Console evidence..."
            today = datetime.now(ZoneInfo("America/Los_Angeles")).date()
            end = today - timedelta(days=3)
            start = end - timedelta(days=29)
            snapshot = await collect_search_console_data(
                access_token=credentials["access_token"], site_url=gsc_site_url,
                start_date=start.isoformat(), end_date=end.isoformat(),
            )
            snapshot["query_pages"] = await self.reviewer.search_console.query_pages(
                credentials["access_token"], gsc_site_url, start, end,
            )
            yield "Checking saved task URLs and sampling current pages..."
            priority_urls = [task["scope"] for task in history["recent_tasks"]]
            priority_urls += [row["keys"][0] for row in snapshot.get("pages", {}).get("rows", []) if row.get("keys")]
            page_cap = {"1-10": 10, "11-30": 12, "31-100": 16, "101-300": 20, "301+": 20}[website_number_of_pages]
            pages = await self.scraper.scrape_from_sitemap(
                self._resolve_sitemap_url(snapshot, site_url), max_pages=page_cap,
                priority_urls=priority_urls, site_url=site_url,
            )
            competitors = []
            try:
                async with asyncio.timeout(20):
                    for value in competitor_urls or []:
                        url = str(value)
                        parsed = urlsplit(url)
                        competitors.append(await self.scraper.scrape_page(url, f"{parsed.scheme}://{parsed.netloc}/"))
            except TimeoutError:
                competitors.append({"fetch_error": "Competitor fetch deadline reached."})

            yield "Reviewing implementation checks and available search results..."
            reviews = await self.reviewer.review(
                site_url, history, pages, credentials["access_token"],
                search_console_site_url=gsc_site_url,
            )
            yield "Loading Core Web Vitals and HTTP header evidence..."
            audit_context = await self._audit_context(site_url, audit_snapshot)
            source_rendering = None
            if self._needs_source_rendering_snapshot(stages, pages):
                source_rendering = await fetch_source_rendering_snapshot(site_url)
            limitations = [
                "Evidence combines Search Console, sampled pages, response headers, Core Web Vitals when available, and compact source-HTML rendering signals; it is not a full browser render, full-site crawl, or live indexing test.",
                "Completed dates are user-reported. Search performance comparisons are directional observations, not proof of causation.",
                "Search Console and model context are sampled. Missing or omitted rows are not proof of zero traffic.",
            ]
            if (audit_context.get("core_web_vitals") or {}).get("status") != "ok":
                limitations.append("Core Web Vitals were unavailable for this run; see saved performance evidence status.")
            if (audit_context.get("http_headers") or {}).get("status") != "ok":
                limitations.append("HTTP header checks were unavailable for this run.")
            if history["tasks_omitted"]:
                limitations.append(f"{history['tasks_omitted']} saved tasks deferred by this run's 12-task review budget.")
            if any(page.get("fetch_error") for page in pages + competitors):
                limitations.append("Some pages were unavailable or exceeded fetch limits; see saved observations.")
            if settings.SEO_DEMO_MODE:
                limitations.append("Model budget mode is enabled, so the prompt uses a representative evidence sample.")
            evidence = {"collected_at": datetime.now(timezone.utc).isoformat(), "pages": pages,
                        "competitors": competitors, "reviews": reviews, "limitations": limitations,
                        "search_console": snapshot, "search_window": {"start": start.isoformat(), "end": end.isoformat()},
                        "search_console_property": gsc_site_url,
                        "core_web_vitals": audit_context.get("core_web_vitals")}

            # Rich snapshots stay in the report; the model sees compact, explicitly bounded records.
            def compact_page(page):
                return {key: value for key, value in page.items() if key != "text_sample"} | {"text_sample": page.get("text_sample", "")[:400]}
            prompt = build_prompt({
                "property": site_url, "size": website_number_of_pages, "website_type": website_type,
                "goal": user_goal, "mode": mode, "focus": focus,
                "search_console_property": gsc_site_url,
                "phase": phase, "assigned_stages": stages or [],
                "covered_stages": history.get("covered_stages", []),
                "search_window": evidence["search_window"],
                "saved_tasks": history["recent_tasks"], "previous_reports": history["previous_reports"],
                "reviews": reviews, "pages": [compact_page(page) for page in pages],
                "competitors": [compact_page(page) for page in competitors],
                "queries": snapshot.get("query_pages", {}).get("rows", [])[:10],
                "query_dimensions": ["query", "page"],
                "core_web_vitals": audit_context.get("core_web_vitals"),
                "http_headers": audit_context.get("http_headers"),
                "source_rendering": source_rendering,
            }, settings.SEO_PROMPT_CHAR_BUDGET or (5760 if settings.SEO_DEMO_MODE else 40000))
            evidence["prompt_omissions"] = json.loads(prompt.split("\nINPUT DATA:\n", 1)[1])["budget_omissions"]
            if evidence["prompt_omissions"]:
                limitations.append("Additional records were summarized to fit the model context; saved history and collected evidence remain available to the app.")
            yield "Preparing findings and next actions..."
            draft = await self._validated_analysis(prompt)
            model_task_count = len(draft.tasks)
            if not draft.tasks:
                fallback_tasks = build_fallback_tasks(
                    pages, snapshot.get("query_pages", {}).get("rows", []),
                )
                if fallback_tasks:
                    logger.warning(
                        "Model returned no tasks for phase=%s; saving %d evidence-backed fallback tasks",
                        phase, len(fallback_tasks),
                    )
                    draft = AnalysisDraft(
                        report=draft.report + "\n\n### Saved actions\nThe task queue includes direct actions from the sampled page and Search Console evidence.",
                        summary=draft.summary,
                        tasks=fallback_tasks,
                    )
            logger.info(
                "SEO task generation site=%s phase=%s assigned_stages=%s model_candidates=%d final_candidates=%d pages=%d query_rows=%d",
                site_url, phase, stages or list(SEO_STAGES), model_task_count, len(draft.tasks), len(pages),
                len(snapshot.get("query_pages", {}).get("rows", [])),
            )
            saved = await self.workspace_service.finish_run(run_id, draft, evidence)
            yield "Preparing sandbox proposals, then saving results to connected apps..."
            coding_result, fastn_result = await self._complete_post_save_handoff(saved.id, UUID(user_id))
            try:
                user = await self.db.scalar(select(User).where(User.id == UUID(user_id)))
                if user:
                    await email_service.send_analysis_summary(
                        user_email=user.email,
                        user_name=user.username or user.email.split("@", 1)[0],
                        site_url=site_url,
                        summary=draft.summary or draft.report[:2000],
                        report_date=datetime.now(timezone.utc).strftime("%B %d, %Y"),
                    )
            except Exception:
                logger.exception("Analysis summary email failed for report %s", saved.id)
            yield {
                "type": "result",
                "report_id": str(saved.id),
                "coding_agent": coding_result,
                "fastn_synced": fastn_result is not None,
            }
            yield STATUS_COMPLETED
        except AnalysisOutputError as error:
            await self.workspace_service.fail_run(run_id)
            yield {"type": "error", "code": "invalid_analysis_output", "message": str(error)}
        except Exception:
            logger.exception("SEO review failed")
            await self.workspace_service.fail_run(run_id)
            yield STATUS_FAILED
