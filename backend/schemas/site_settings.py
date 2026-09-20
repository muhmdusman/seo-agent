from pydantic import BaseModel, ConfigDict, Field


class SiteSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    github_repo_url: str = Field(default="", max_length=500)


class SiteSettingsResponse(BaseModel):
    site_url: str
    github_repo_url: str
    github_owner: str
    github_repo: str
