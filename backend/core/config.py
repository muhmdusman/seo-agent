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
    
    # Email Service Configuration (SMTP)
    SMTP_HOST: str = Field(default="smtp.gmail.com")
    SMTP_PORT: int = Field(default=587)
    SMTP_USERNAME: str = Field(...)
    SMTP_PASSWORD: str = Field(...)
    SMTP_FROM_EMAIL: str = Field(...)
    SMTP_FROM_NAME: str = Field(default="Search Console Agent")
    
    # Scheduler Configuration
    SCHEDULER_ENABLED: bool = True
    DAILY_REPORT_TIME: str = "08:00"
    ADMIN_EMAIL: str = Field(...)

    #redis config
    # REDIS_HOST:str = Field(...)|"localhost"
    # REDIS_PORT:int = Field(...)|6379
    REDIS_URL: str = Field("redis://localhost:6379/0")
 

@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()