from datetime import datetime

from pydantic import BaseModel


class GoogleTokenResponse(BaseModel):
    access_token: str

    expires_in: int

    refresh_token: str | None = None

    scope: str

    token_type: str

    id_token: str

    expires_at: datetime | None = None