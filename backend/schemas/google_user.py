from pydantic import BaseModel, EmailStr


class GoogleUserInfo(BaseModel):
    google_id: str
    email: EmailStr
    email_verified: bool
    username:str