from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


Stage = Literal[
    "technical-foundation", "crawlability", "rendering", "indexability",
    "on-page", "content", "search-intent", "semantic-seo", "ai-geo",
]
STAGES = list(Stage.__args__)
STAGE_GROUPS = [STAGES[:4], STAGES[4:6], STAGES[6:8], STAGES[8:]]
NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


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


class AnalysisDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report: Annotated[NonEmpty, Field(max_length=60000)]
    summary: str = Field(default="", max_length=4000)
    tasks: list[TaskDraft] = Field(max_length=12)


class AnalysisRequest(BaseModel):
    site_url: Annotated[NonEmpty, Field(max_length=2000)]
    website_number_of_pages: Literal["1-10", "11-30", "31-100", "101-300", "301+"]
    website_type: Annotated[NonEmpty, Field(max_length=200)]
    user_goal: Annotated[NonEmpty, Field(max_length=500)]


class CompletionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    completed: bool


def next_stages(covered: set[str], size: str) -> list[str]:
    cap = {"1-10": 4, "11-30": 3, "31-100": 2, "101-300": 1, "301+": 1}[size]
    for group in STAGE_GROUPS:
        remaining = [stage for stage in group if stage not in covered]
        if remaining:
            return remaining[:cap]
    return []
