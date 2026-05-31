"""Celery configuration for the LLM Red-Team Platform workers."""

import os

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "UTC"
enable_utc = True

task_track_started = True
task_time_limit = 3600  # 1 hour max per task
task_soft_time_limit = 3000  # Soft limit at 50 min

worker_prefetch_multiplier = 1  # One task at a time per worker process
worker_concurrency = 4
