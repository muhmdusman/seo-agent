from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FastnWorkflowExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    input: dict[str, Any] | None = Field(
        default=None,
        description="Raw payload to pass to the Fastn workflow.",
    )
    site_url: str | None = Field(default=None, alias="siteUrl", max_length=2000)
    website_size: Literal["1-10", "11-30", "31-100", "101-300", "301+"] | None = None
    website_number_of_pages: Literal["1-10", "11-30", "31-100", "101-300", "301+"] | None = None
    website_type: str | None = Field(default=None, max_length=200)
    user_goal: str | None = Field(default=None, max_length=500)

    def workflow_input(self) -> dict[str, Any]:
        payload = dict(self.input or {})

        if self.site_url is not None:
            payload["siteUrl"] = self.site_url
        if self.website_size is not None:
            payload["website_size"] = self.website_size
        elif self.website_number_of_pages is not None:
            payload["website_size"] = self.website_number_of_pages
        if self.website_type is not None:
            payload["website_type"] = self.website_type
        if self.user_goal is not None:
            payload["user_goal"] = self.user_goal

        for key, value in (self.model_extra or {}).items():
            if key != "input" and value is not None:
                payload[key] = value

        return payload


class FastnWorkflowExecuteResponse(BaseModel):
    workflow_id: str
    status_code: int
    result: dict[str, Any]
