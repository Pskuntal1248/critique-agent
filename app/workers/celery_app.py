"""Celery application — uses Redis as broker and result backend."""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "critique",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.graph_worker"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # One task at a time per worker process (LLM calls are slow; don't pile up)
    worker_prefetch_multiplier=1,
    # Keep results for 24 h
    result_expires=86400,
)
