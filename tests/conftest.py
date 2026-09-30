"""Shared fixtures for Critique tests."""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.models.agent_event import AgentEvent  # noqa: F401
from app.models.agent_step import AgentStep  # noqa: F401
from app.models.base import Base
from app.models.database import get_db
from app.models.task_run import TaskRun  # noqa: F401 — register with metadata


@pytest.fixture
async def db_session(tmp_path):
    db_file = str(tmp_path / "test.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def sample_task() -> str:
    return "Research the fintech market in Chile and identify top 3 opportunities"


@pytest.fixture
async def async_client(db_session: AsyncSession):
    """AsyncClient wired to the FastAPI app with the test DB session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    app.dependency_overrides.clear()


def make_task_run(
    task_id: str | None = None,
    status: str = "pending",
    task: str = "Research the fintech market in Chile",
    human_in_loop: bool = False,
) -> MagicMock:
    """Return a MagicMock shaped like a TaskRun ORM object."""
    run = MagicMock()
    run.id = uuid.UUID(task_id) if task_id else uuid.uuid4()
    run.original_task = task
    run.status = status
    run.human_in_loop = human_in_loop
    run.critic_score = None
    run.revision_count = 0
    run.total_tokens = 0
    run.total_prompt_tokens = 0
    run.total_completion_tokens = 0
    run.estimated_cost_usd = None
    run.model_name = None
    run.llm_provider = None
    run.celery_task_id = None
    run.total_duration_ms = None
    run.final_report = None
    run.error = None
    run.created_at = datetime.now(UTC)
    run.updated_at = datetime.now(UTC)
    return run


@pytest.fixture
def base_state(sample_task) -> dict:
    """Minimal valid AgentState dict for node testing."""
    return {
        "task_id": "test-task-123",
        "original_task": sample_task,
        "subtasks": [],
        "research_results": [],
        "analysis": "",
        "critic_score": 0.0,
        "critic_feedback": "",
        "critic_approved": False,
        "revision_count": 0,
        "human_in_loop": False,
        "human_decision": None,
        "human_feedback": None,
        "final_report": None,
        "status": "pending",
        "active_agent": "",
        "tokens_used": 0,
        "prompt_tokens_used": 0,
        "completion_tokens_used": 0,
        "errors": [],
        "messages": [],
    }
