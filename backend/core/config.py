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
    REFRESH_TOKEN_EXPIRY_DAYS:int = Field(...)

    # Shrinks agent prompts to fit a low tokens-per-minute allowance, at the
    # cost of analysis depth. Set to false once the provider account has a
    # higher rate limit.
    SEO_DEMO_MODE: bool = Field(default=True)
    # Optional override for the local prompt-size guard; provider token quotas vary.
    SEO_PROMPT_CHAR_BUDGET: int = Field(default=0, ge=0, le=100000)

    # ------------------------------------------------------------------
    # LLM provider
    # ------------------------------------------------------------------
    # Both agents talk to the model through LiteLLM, so the provider is
    # selected by the model id prefix. Keeping the id here means the weekly
    # agent, the daily agent, and check_rate_limit.py cannot drift apart.
    #
    # Env var names are matched case-insensitively, so GROQ_API_KEY,
    # Groq_Api_Key, and groq_api_key in .env all populate this field.
    GROQ_API_KEY: str = Field(...)
    LLM_MODEL_ID: str = Field(default="groq/openai/gpt-oss-120b")

    # Optional: only needed if LLM_MODEL_ID is pointed back at a mistral/ id.
    MISTRAL_API_KEY: str = Field(default="")

    # PageSpeed Insights / Core Web Vitals. Optional at import time so tests
    # and non-performance environments can still boot.
    PAGESPEED_API_KEY: str = Field(default="")
    
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

    # Fastn workflow execution. The API key is optional at startup so local
    # development and tests can boot without the integration configured.
    FASTN_API_BASE_URL: str = Field(default="https://api.fastn.dev")
    FASTN_WORKFLOW_ID: str = Field(default="wf_3dd1351b36da")
    FASTN_DESTINATIONS_WORKFLOW_ID: str = Field(default="wf_84cad8eacfc8")
    FASTN_WIDGET_ID: str = Field(default="wgt_e50e98094782")
    FASTN_API_KEY: str = Field(default="")
    FASTN_AUTH_HEADER: str = Field(default="Authorization")
    FASTN_AUTH_SCHEME: str = Field(default="Bearer")
    FASTN_TENANT_HEADER: str = Field(default="x-end-org-id")
    FASTN_INSTALLATION_HEADER: str = Field(default="x-installation-id")
    FASTN_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0)

    #redis config
    # REDIS_HOST:str = Field(...)|"localhost"
    # REDIS_PORT:int = Field(...)|6379
    REDIS_URL: str = Field("redis://redis:6379/0")

    @property
    def LLM_API_KEY(self) -> str:
        """Return the credential matching the provider prefix in LLM_MODEL_ID."""
        provider = self.LLM_MODEL_ID.split("/", 1)[0].strip().lower()

        if provider == "mistral":
            return self.MISTRAL_API_KEY

        return self.GROQ_API_KEY


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
