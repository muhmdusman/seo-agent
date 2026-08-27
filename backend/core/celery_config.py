from core.config import settings


CELERY_CONFIG = {
    "broker_url": settings.REDIS_URL,

    "task_serializer": "json",
    "accept_content": ["json"],

    "timezone": "UTC",
    "enable_utc": True,
}