from pydantic import BaseModel, ConfigDict, Field


class SiteSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    github_repo_url: str = Field(default="", max_length=500)
    github_owner: str = Field(default="", max_length=100)
    github_repo: str = Field(default="", max_length=200)
    google_spreadsheet_id: str = Field(default="", max_length=200)
    google_spreadsheet_name: str = Field(default="", max_length=500)


class SiteSettingsResponse(BaseModel):
    site_url: str
    github_repo_url: str
    github_owner: str
    github_repo: str
    google_spreadsheet_id: str
    google_spreadsheet_name: str
