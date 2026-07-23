from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    
    APP_NAME:str = Field(...)
    DEBUG: bool = False

    DATABASE_URL: str = Field(...)

    GOOGLE_CLIENT_ID: str = Field(...)
    GOOGLE_CLIENT_SECRET: str = Field(...)
    GOOGLE_REDIRECT_URI:str = Field()

    JWT_SECRET: str = Field(...)
    JWT_ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    APP_URL:str = Field(...)
    FRONTEND_URL: str = Field(...)
    MISTRAL_API_KEY:str = Field(...)
    REFRESH_TOKEN_EXPIRY_DAYS:int = Field(...)



@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()