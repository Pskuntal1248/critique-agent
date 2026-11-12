"""Single-process, ephemeral-storage demo deployment.

Run: uvicorn demo_server:app --host 0.0.0.0 --port $PORT --workers 1
SQLite data resets on Render restarts. No production durability is implied.
The original Docker/Postgres/Celery deployment remains unchanged.
"""
import asyncio
import os
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from statistics import mean
from types import SimpleNamespace

os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:////tmp/critique-demo.db')

# Optional strictly free, OpenAI-compatible provider. Never fall back to a
# paid provider automatically. The account owner must select the provider.
if os.getenv('FREE_LLM_API_KEY'):
    from langchain_openai import ChatOpenAI
    import app.services.llm.base as llm_base

    def free_llm(temperature=0.3):
        return ChatOpenAI(
            model=os.environ['FREE_LLM_MODEL'],
            base_url=os.environ['FREE_LLM_BASE_URL'],
            api_key=os.environ['FREE_LLM_API_KEY'],
            temperature=temperature,
            max_tokens=2048,
            max_retries=1,
            timeout=45,
        )
    llm_base.get_llm = free_llm

from fastapi import HTTPException, Request
from sqlalchemy import select
from app.workers import graph_worker
from app.models.database import create_tables
from app.models.task_run import TaskRun
from app.models.agent_step import AgentStep
import app.services.metrics_service as metrics_service

_jobs = {}
_job_started = {}

class LocalQueue:
    def delay(self, task_id, original_task, human_in_loop):
        job = asyncio.create_task(graph_worker._run_graph_async(task_id, original_task, human_in_loop))
        _jobs[task_id] = job
        _job_started[task_id] = time.monotonic()
        job.add_done_callback(lambda _: _jobs.pop(task_id, None))
        return SimpleNamespace(id=task_id)

graph_worker.run_graph = LocalQueue()
# Cancellation uses this object's control API. Keep it local, never contact Redis.
def revoke(task_id, **kwargs):
    job = _jobs.get(task_id)
    if job:
        job.cancel()
graph_worker.celery_app.control.revoke = revoke

async def sqlite_metrics(db, hours=24):
    since = datetime.now(UTC) - timedelta(hours=hours)
    runs = list(await db.scalars(select(TaskRun).where(TaskRun.created_at >= since)))
    steps = list(await db.scalars(select(AgentStep).where(AgentStep.created_at >= since)))
    durations = sorted(r.total_duration_ms or 0 for r in runs)
    agents = {}
    for step in steps:
        agents.setdefault(step.agent_name, []).append(step.duration_ms or 0)
    return {
        'period_hours': hours, 'runs_total': len(runs),
        'runs_successful': sum(r.status in ('complete', 'best_effort') for r in runs),
        'success_rate_pct': round(100 * sum(r.status in ('complete', 'best_effort') for r in runs) / len(runs), 1) if runs else 0,
        'avg_duration_ms': round(mean(durations)) if durations else 0,
        'p95_duration_ms': durations[min(len(durations)-1, int(len(durations)*.95))] if durations else 0,
        'avg_tokens_per_run': round(mean(r.total_tokens for r in runs)) if runs else 0,
        'avg_revisions': round(mean(r.revision_count for r in runs), 2) if runs else 0,
        'agent_avg_latency_ms': {k: round(mean(v)) for k, v in agents.items()},
    }
metrics_service.get_metrics = sqlite_metrics

from app.main import app
original_lifespan = app.router.lifespan_context

@asynccontextmanager
async def demo_lifespan(application):
    await create_tables()
    async with original_lifespan(application):
        yield
    for job in list(_jobs.values()):
        job.cancel()
app.router.lifespan_context = demo_lifespan

_recent_starts = []
@app.middleware('http')
async def demo_limits(request: Request, call_next):
    from starlette.responses import JSONResponse
    if request.method == 'POST' and request.url.path == '/tasks':
        if not os.getenv('FREE_LLM_API_KEY'):
            return JSONResponse({'detail': 'Live research is not enabled: a free-tier model provider must be configured.'}, status_code=503)
        now = time.monotonic()
        _recent_starts[:] = [t for t in _recent_starts if now-t < 86400]
        if _jobs or len(_recent_starts) >= 10:
            return JSONResponse({'detail': 'Free demo limit reached. One concurrent run and ten runs per day.'}, status_code=429)
        _recent_starts.append(now)
    return await call_next(request)

@app.get('/demo-info')
async def demo_info():
    return {'mode': 'free-tier-demo', 'live_model_enabled': bool(os.getenv('FREE_LLM_API_KEY')),
            'storage': 'ephemeral SQLite; resets on restarts',
            'limits': 'one concurrent run; ten runs per day',
            'source': 'https://github.com/Pskuntal1248/critique-agent',
            'credit': 'Adapted from AgentForge'}
