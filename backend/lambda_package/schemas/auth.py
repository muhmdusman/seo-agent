from pydantic import BaseModel, EmailStr


class GoogleRegisterData(BaseModel):
    google_id: str
    email: EmailStr
    email_verified: bool
