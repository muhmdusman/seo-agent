from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints

from core.seo_framework import SEO_STAGES

# Backward-compatible export for callers/tests. The workflow itself lives in
# core.seo_framework so stage order and sub-frameworks have one source of truth.
CORE_STAGES = list(SEO_STAGES)
Stage = Literal[
    "technical-foundation", "crawlability", "rendering", "indexability",
    "on-page", "content", "search-intent", "semantic-seo", "ai-geo",
]
NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class VerificationCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: Literal["title", "meta_description", "canonical", "h1", "noindex", "viewport", "status_code"]
    expected: Annotated[NonEmpty, Field(max_length=500)]


class TaskDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: Stage
    title: Annotated[NonEmpty, Field(max_length=200)]
    priority: Literal["critical", "high", "medium", "quick-win"]
    scope: Annotated[NonEmpty, Field(max_length=2000)]
    evidence: Annotated[NonEmpty, Field(max_length=2000)]
    why_it_matters: Annotated[NonEmpty, Field(max_length=2000)]
    manual_fix: Annotated[NonEmpty, Field(max_length=4000)]
    agent_prompt: Annotated[NonEmpty, Field(max_length=4000)]
    subtasks: list[Annotated[NonEmpty, Field(max_length=500)]] = Field(min_length=1, max_length=8)
    verification: VerificationCheck | None = Field(
        default=None,
        description="Always include this key. Use null unless there is one exact observable condition to verify.",
    )
    existing_task_id: str | None = Field(
        default=None,
        max_length=36,
        description="Always include this key. Use null for new tasks; only use a saved task id when updating that task.",
    )


class AnalysisDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report: Annotated[NonEmpty, Field(max_length=60000)]
    summary: str = Field(default="", max_length=4000)
    tasks: list[TaskDraft] = Field(max_length=12)


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    site_url: Annotated[NonEmpty, Field(max_length=2000)]
    website_number_of_pages: Literal["1-10", "11-30", "31-100", "101-300", "301+"]
    website_type: Annotated[NonEmpty, Field(max_length=200)]
    user_goal: Annotated[NonEmpty, Field(max_length=500)]
    mode: Literal["auto", "review", "growth"] = "auto"
    focus: str = Field(default="", max_length=500)
    competitor_urls: list[HttpUrl] = Field(default_factory=list, max_length=3)
    audit_snapshot: dict[str, Any] | None = Field(
        default=None,
        description="Compact Core Web Vitals and HTTP header context fetched by the backend audit endpoint.",
    )


class AuditSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_url: str
    url: str
    collected_at: str
    core_web_vitals: dict[str, Any]
    http_headers: dict[str, Any]
    compact_context: dict[str, Any]


class CompletionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    completed: bool
