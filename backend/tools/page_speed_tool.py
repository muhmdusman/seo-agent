"""PageSpeed Insights/Core Web Vitals collection and compaction."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

from core.config import settings
from tools.source_html_tool import property_home_url

PAGESPEED_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
STRATEGIES = ("mobile", "desktop")
CATEGORIES = ("performance", "accessibility", "best-practices", "seo")
STRATEGY_TIMEOUT_SECONDS = 18

FIELD_METRICS = {
    "FIRST_CONTENTFUL_PAINT_MS": ("fcp", "First Contentful Paint", "ms", 1),
    "LARGEST_CONTENTFUL_PAINT_MS": ("lcp", "Largest Contentful Paint", "ms", 1),
    "INTERACTION_TO_NEXT_PAINT": ("inp", "Interaction to Next Paint", "ms", 1),
    "CUMULATIVE_LAYOUT_SHIFT_SCORE": ("cls", "Cumulative Layout Shift", "score", 0.01),
}

LAB_AUDITS = {
    "first-contentful-paint": ("fcp", "First Contentful Paint"),
    "largest-contentful-paint": ("lcp", "Largest Contentful Paint"),
    "total-blocking-time": ("tbt", "Total Blocking Time"),
    "cumulative-layout-shift": ("cls", "Cumulative Layout Shift"),
    "speed-index": ("speed_index", "Speed Index"),
    "interactive": ("tti", "Time to Interactive"),
}


def _score(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return round(float(value) * 100)
    except (TypeError, ValueError):
        return None


def _field_metric(key: str, metric: dict[str, Any]) -> dict[str, Any] | None:
    definition = FIELD_METRICS.get(key)
    if not definition:
        return None
    slug, label, unit, multiplier = definition
    raw_value = metric.get("percentile")
    try:
        value = round(float(raw_value) * multiplier, 3 if unit == "score" else 0)
    except (TypeError, ValueError):
        value = None
    return {
        "key": slug,
        "label": label,
        "value": value,
        "unit": unit,
        "display_value": _display_value(value, unit),
        "category": metric.get("category", "UNKNOWN"),
    }


def _display_value(value: int | float | None, unit: str) -> str:
    if value is None:
        return "n/a"
    if unit == "ms":
        return f"{value / 1000:.1f}s" if value >= 1000 else f"{round(value)}ms"
    if unit == "score":
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)


def _lab_metric(audit_id: str, audit: dict[str, Any]) -> dict[str, Any] | None:
    definition = LAB_AUDITS.get(audit_id)
    if not definition:
        return None
    slug, label = definition
    numeric = audit.get("numericValue")
    unit = "score" if slug == "cls" else "ms"
    try:
        value = round(float(numeric), 3 if unit == "score" else 0)
    except (TypeError, ValueError):
        value = None
    return {
        "key": slug,
        "label": label,
        "value": value,
        "unit": unit,
        "display_value": audit.get("displayValue") or _display_value(value, unit),
        "score": _score(audit.get("score")),
    }


def _opportunity(audit_id: str, audit: dict[str, Any]) -> dict[str, Any] | None:
    mode = audit.get("scoreDisplayMode")
    if mode not in {"opportunity", "numeric"}:
        return None
    details = audit.get("details") or {}
    savings = details.get("overallSavingsMs")
    score = audit.get("score")
    if savings in (None, 0) and (score is None or score >= 0.9):
        return None
    try:
        numeric_savings = round(float(savings or audit.get("numericValue") or 0))
    except (TypeError, ValueError):
        numeric_savings = 0
    return {
        "id": audit_id,
        "label": audit.get("title", audit_id),
        "detail": audit.get("displayValue") or (f"{numeric_savings}ms potential savings" if numeric_savings else "Needs review"),
        "score": _score(score),
        "savings_ms": numeric_savings,
    }


def summarize_pagespeed_result(payload: dict[str, Any], strategy: str) -> dict[str, Any]:
    """Normalize one PageSpeed response to UI/report-friendly fields."""
    lighthouse = payload.get("lighthouseResult") or {}
    categories = lighthouse.get("categories") or {}
    audits = lighthouse.get("audits") or {}
    loading = payload.get("loadingExperience") or {}
    field_metrics = {
        normalized["key"]: normalized
        for key, metric in (loading.get("metrics") or {}).items()
        if (normalized := _field_metric(key, metric))
    }
    lab_metrics = {
        normalized["key"]: normalized
        for audit_id, audit in audits.items()
        if (normalized := _lab_metric(audit_id, audit))
    }
    opportunities = [
        item for audit_id, audit in audits.items()
        if (item := _opportunity(audit_id, audit))
    ]
    opportunities.sort(key=lambda item: (item.get("savings_ms") or 0, item.get("score") or 100), reverse=True)
    return {
        "strategy": strategy,
        "requested_url": lighthouse.get("requestedUrl") or payload.get("id"),
        "final_url": lighthouse.get("finalUrl") or payload.get("id"),
        "fetch_time": lighthouse.get("fetchTime"),
        "lighthouse_version": lighthouse.get("lighthouseVersion"),
        "overall_category": loading.get("overall_category"),
        "origin_fallback": bool(loading.get("origin_fallback", False)),
        "scores": {
            "performance": _score((categories.get("performance") or {}).get("score")),
            "accessibility": _score((categories.get("accessibility") or {}).get("score")),
            "best_practices": _score((categories.get("best-practices") or {}).get("score")),
            "seo": _score((categories.get("seo") or {}).get("score")),
        },
        "field": field_metrics,
        "lab": lab_metrics,
        "opportunities": opportunities[:6],
        "warnings": lighthouse.get("runWarnings") or [],
    }


async def _run_pagespeed(url: str, strategy: str) -> dict[str, Any]:
    params: list[tuple[str, str]] = [("url", url), ("strategy", strategy), ("key", settings.PAGESPEED_API_KEY)]
    params.extend(("category", category) for category in CATEGORIES)
    async with asyncio.timeout(STRATEGY_TIMEOUT_SECONDS):
        async with httpx.AsyncClient(timeout=httpx.Timeout(STRATEGY_TIMEOUT_SECONDS, connect=5), trust_env=False) as client:
            response = await client.get(PAGESPEED_ENDPOINT, params=params)
            response.raise_for_status()
            return summarize_pagespeed_result(response.json(), strategy)


async def fetch_core_web_vitals(site_url: str) -> dict[str, Any]:
    """Fetch mobile and desktop PageSpeed snapshots for a Search Console property."""
    collected_at = datetime.now(timezone.utc).isoformat()
    try:
        url = property_home_url(site_url)
    except ValueError as exc:
        return {
            "status": "unavailable",
            "collected_at": collected_at,
            "url": site_url,
            "error": str(exc),
            "strategies": {},
        }
    if not settings.PAGESPEED_API_KEY:
        return {
            "status": "unavailable",
            "collected_at": collected_at,
            "url": url,
            "error": "PAGESPEED_API_KEY is not configured.",
            "strategies": {},
        }
    results = await asyncio.gather(*(_run_pagespeed(url, strategy) for strategy in STRATEGIES), return_exceptions=True)
    strategies: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for strategy, result in zip(STRATEGIES, results):
        if isinstance(result, Exception):
            errors[strategy] = type(result).__name__
        else:
            strategies[strategy] = result
    status = "ok" if strategies else "unavailable"
    return {
        "status": status,
        "collected_at": collected_at,
        "url": url,
        "strategies": strategies,
        "errors": errors,
    }


def compact_core_web_vitals(snapshot: dict[str, Any] | None) -> dict[str, Any] | None:
    """Keep only numeric progress metrics for report storage and LLM context."""
    if not snapshot:
        return None
    compact = {
        "status": snapshot.get("status"),
        "collected_at": snapshot.get("collected_at"),
        "url": snapshot.get("url"),
        "strategies": {},
    }
    for strategy, data in (snapshot.get("strategies") or {}).items():
        compact["strategies"][strategy] = {
            "scores": data.get("scores") or {},
            "field": {
                key: {
                    "value": metric.get("value"),
                    "unit": metric.get("unit"),
                    "display_value": metric.get("display_value"),
                    "category": metric.get("category"),
                }
                for key, metric in (data.get("field") or {}).items()
            },
            "lab": {
                key: {
                    "value": metric.get("value"),
                    "unit": metric.get("unit"),
                    "display_value": metric.get("display_value"),
                    "score": metric.get("score"),
                }
                for key, metric in (data.get("lab") or {}).items()
            },
        }
    if snapshot.get("errors"):
        compact["errors"] = snapshot["errors"]
    if snapshot.get("error"):
        compact["error"] = snapshot["error"]
    return compact
