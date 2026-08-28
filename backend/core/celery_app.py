from celery import Celery

from core.celery_config import CELERY_CONFIG


celery_app = Celery(
    "seo_agent",
)

celery_app.conf.update(CELERY_CONFIG)

celery_app.conf.imports = (
    "workers.daily_report_worker",
)