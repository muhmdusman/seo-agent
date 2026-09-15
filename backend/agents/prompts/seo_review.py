"""Build the bounded SEO review prompt from the staged framework and evidence."""

import json
import re
from copy import deepcopy
from pathlib import Path

from core.seo_framework import SEO_STAGES, STAGE_CAPS, STAGE_FRAMEWORKS, stage_group

SKILL_PATH = Path(__file__).resolve().parents[2] / "system-prompt" / "SKILL.md"

CONTRACT = """Return only JSON: {"report": "Markdown findings, changes, limitations and next steps", "summary": "factual history", "tasks": []}.
Tasks must use one of the nine core stage slugs supplied in the framework context. The extra lenses (local-seo, ecommerce, international-seo, internal-linking, competitor-analysis and competitor-research) are topics inside those stages, not additional stages.
Each task must include stage, title, priority (critical/high/medium/quick-win), scope (one exact URL or property), evidence, why_it_matters, manual_fix, agent_prompt, subtasks (1-5 strings), existing_task_id and verification.
Set existing_task_id to null for new tasks; only use a saved task id when the task updates an issue already in saved context.
Set verification to null for broader recommendations. Otherwise verification is {"field": "title|meta_description|canonical|h1|noindex|viewport|status_code", "expected": "exact expected value"}; pick ONE field, not the pipe-separated list. Only supply this for an observable unmet condition at the exact scope URL.
Never all 9 stages in one turn. Use only the assigned bundle until the framework is covered.
Use at most 4 tasks and 500 report words. Do not generate dates, completion, status or verification-action fields; the server owns those. Cite only supplied evidence and disclose omitted samples. During the visibility-opportunities or change-review phase, review saved changes/results and choose a relevant core stage without reopening the sequence. Empty tasks are valid only when the evidence supports no new action or all useful actions are already saved.
Only supply verification for an observable unmet condition at the exact scope URL.
Use Core Web Vitals and HTTP headers as supporting evidence only. Do not invent Lighthouse issues beyond supplied compact metrics and headers.
Use source_rendering only to reason about whether the page appears server-rendered, prerendered, mixed, or client-rendered. It is compact source-HTML metadata, not full browser rendering or full source HTML.
"""


def _load_skill() -> str:
    """Inject a compact operational excerpt while keeping SKILL.md authoritative."""
    source = SKILL_PATH.read_text(encoding="utf-8")
    wanted = ("## Tools", "## Step 2 — Tools", "## Resume", "## Step 3 — Resume logic", "## Principles")
    sections = []
    for heading in wanted:
        start = source.find(heading)
        if start < 0:
            continue
        end = len(source)
        for next_heading in wanted:
            candidate = source.find(next_heading, start + len(heading))
            if candidate >= 0:
                end = min(end, candidate)
        lines = []
        for line in source[start:end].splitlines():
            line = re.sub(r"\s+", " ", line).strip()
            if line.startswith(("##", "-", "**")):
                lines.append(line)
        if lines:
            sections.append("\n".join(lines))
    return "# Staged SEO Growth Agent\n" + "\n".join(sections)[:1400]


def _framework_context(assigned_stages: list[str], phase: str) -> dict:
    if phase == "framework":
        stages = assigned_stages
        instruction = "Analyze only the assigned stages and their listed lenses in this bounded run."
    else:
        stages = list(SEO_STAGES)
        instruction = (
            "The nine-stage framework is covered. Review saved changes and their results, "
            "then find new visibility opportunities or competitor research supported by the evidence. "
            "Use a relevant core stage label without reopening the sequential framework."
        )
    framework = {
        "phase": phase,
        "instruction": instruction,
        "assigned_stages": stages,
        "stage_groups": {stage: stage_group(stage) for stage in stages},
        "stage_caps": STAGE_CAPS,
    }
    if phase == "framework":
        framework["stage_frameworks"] = {stage: STAGE_FRAMEWORKS[stage] for stage in stages}
    else:
        framework["available_lenses"] = [
            "local-seo", "ecommerce", "international-seo", "internal-linking",
            "competitor-analysis", "competitor-research",
        ]
    return framework


def build_prompt(context: dict, max_chars: int) -> str:
    skill = _load_skill()
    data = deepcopy(context)
    assigned_stages = data.pop("assigned_stages", [])
    phase = data.pop("phase", "framework")
    data["framework"] = _framework_context(assigned_stages, phase)
    data["budget_omissions"] = {}

    def render():
        return skill + "\n\n" + CONTRACT + "\nINPUT DATA:\n" + json.dumps(data, separators=(",", ":"), ensure_ascii=True)

    # Whole records are removed, never half a URL, JSON object or instruction.
    groups = ["previous_reports", "queries", "pages", "competitors", "saved_tasks", "reviews"]
    optional_context = ["source_rendering", "http_headers", "core_web_vitals"]
    while len(render()) > max_chars:
        candidates = [key for key in groups if data.get(key)]
        if not candidates:
            removable_context = [key for key in optional_context if data.get(key)]
            if not removable_context:
                raise ValueError("The configured SEO prompt budget cannot hold the skill and request context.")
            key = removable_context[0]
            data[key] = None
            data["budget_omissions"][key] = 1
            continue
        # Keep one representative record from each source whenever possible.
        removable = [key for key in candidates if len(data[key]) > 1] or candidates
        key = max(removable, key=lambda item: len(json.dumps(data[item])))
        data[key].pop()
        data["budget_omissions"][key] = data["budget_omissions"].get(key, 0) + 1
    return render()
