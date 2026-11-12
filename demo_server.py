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

# Credentials are scoped to the current request and inherited by its task.
# They never enter environment variables, database records or API responses.
from contextvars import ContextVar
_credentials = ContextVar('byok', default=None)
_visitor = ContextVar('visitor', default=None)
_provider_urls = {
    'openai': 'https://api.openai.com/v1',
    'openrouter': 'https://openrouter.ai/api/v1',
    'gemini': 'https://generativelanguage.googleapis.com/v1beta/openai',
    'groq': 'https://api.groq.com/openai/v1',
}
import app.services.llm.base as llm_base

def byok_llm(temperature=0.3):
    cred = _credentials.get()
    if not cred:
        raise ValueError('Configure your provider and API key in Settings.')
    provider, model, key, session = cred
    if provider == 'anthropic':
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, api_key=key, temperature=temperature,
                             max_tokens=2048, max_retries=1, timeout=45)
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=model, base_url=_provider_urls[provider], api_key=key,
                      temperature=temperature, max_tokens=2048, max_retries=1, timeout=45)
llm_base.get_llm = byok_llm

from fastapi import HTTPException, Request
from sqlalchemy import select
from app.workers import graph_worker
from app.models.database import create_tables
from app.models.task_run import TaskRun
from app.models.agent_step import AgentStep
import app.services.metrics_service as metrics_service

_jobs = {}
_owners = {}
_job_started = {}

class LocalQueue:
    def delay(self, task_id, original_task, human_in_loop):
        _owners[task_id] = _credentials.get()[3]
        job = asyncio.create_task(asyncio.wait_for(graph_worker._run_graph_async(task_id, original_task, human_in_loop), timeout=600))
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
    ids = [k for k, v in _owners.items() if v == _visitor.get()]
    runs = list(await db.scalars(select(TaskRun).where(TaskRun.created_at >= since, TaskRun.id.in_(ids))))
    steps = list(await db.scalars(select(AgentStep).where(AgentStep.created_at >= since, AgentStep.task_id.in_(ids))))
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
    if request.method == 'OPTIONS':
        return await call_next(request)
    session = request.headers.get('x-demo-session') or request.query_params.get('session')
    task_id = request.url.path.split('/')[2] if request.url.path.startswith('/tasks/') else None
    if task_id and (not session or _owners.get(task_id) != session):
        return JSONResponse({'detail': 'Task not found in this browser session.'}, status_code=404)
    cred_token = None
    if request.method == 'POST' and request.url.path == '/tasks':
        provider = request.headers.get('x-llm-provider', '')
        model = request.headers.get('x-llm-model', '')
        key = request.headers.get('x-llm-key', '')
        if provider not in {*_provider_urls, 'anthropic'} or not model or not key or not session:
            return JSONResponse({'detail': 'Configure provider, model and API key in Settings first.'}, status_code=400)
        if len(key)>4096 or len(model)>200 or len(session)>100:
            return JSONResponse({'detail': 'Invalid settings.'}, status_code=400)
        now = time.monotonic()
        _recent_starts[:] = [t for t in _recent_starts if now-t < 3600]
        if len(_jobs)>=3 or len(_recent_starts)>=30:
            return JSONResponse({'detail': 'Free demo is busy. Please try again later.'}, status_code=429)
        _recent_starts.append(now)
        cred_token = _credentials.set((provider, model, key, session))
    try:
        visitor_token = _visitor.set(session)
        response = await call_next(request)
        _visitor.reset(visitor_token)
        # List and aggregate endpoints only expose this visitor's runs.
        if request.method=='GET' and request.url.path=='/tasks':
            import json
            body = b''.join([chunk async for chunk in response.body_iterator])
            data = json.loads(body)
            if isinstance(data, list):
                return JSONResponse([r for r in data if _owners.get(r['task_id']) == session])
        return response
    finally:
        if cred_token is not None:
            _credentials.reset(cred_token)

@app.post('/byok/models')
async def provider_models(request: Request):
    import httpx
    body = await request.json()
    provider, key = body.get('provider'), body.get('key')
    if provider not in {*_provider_urls, 'anthropic'} or not isinstance(key, str) or not key or len(key)>4096:
        raise HTTPException(400, 'Provider and key required.')
    headers = {'Authorization': f'Bearer {key}'}
    url = _provider_urls.get(provider, '') + '/models'
    if provider == 'anthropic':
        url = 'https://api.anthropic.com/v1/models'
        headers = {'x-api-key': key, 'anthropic-version': '2023-06-01'}
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise HTTPException(400, 'Provider rejected model lookup. Check your API key and access.')
            payload = response.json()
            models = sorted({m['id'] for m in payload.get('data', []) if isinstance(m, dict) and isinstance(m.get('id'), str)})
            return {'models': models}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, 'Model provider could not be reached.')

@app.get('/demo-info')
async def demo_info():
    return {'mode': 'bring-your-own-key',
            'storage': 'ephemeral SQLite; resets on restarts',
            'credentials': 'Browser session storage; transmitted to backend only for provider requests, never persisted server-side',
            'source': 'https://github.com/Pskuntal1248/critique-agent',
            'credit': 'Adapted from AgentForge'}
