"""Tests for GET /tasks/{id}/events and GET /tasks/{id}/steps."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_event import AgentEvent
from app.models.agent_step import AgentStep
from app.models.task_run import TaskRun

# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
async def seeded_task(db_session: AsyncSession):
    """Insert a task_run + one event + one step into the test DB."""
    task_uuid = uuid.uuid4()

    run = TaskRun(
        id=task_uuid,
        original_task="Research fintech trends in Chile.",
        status="complete",
        human_in_loop=False,
    )
    db_session.add(run)
    await db_session.commit()

    event = AgentEvent(
        task_id=task_uuid,
        event_type="agent_start",
        agent_name="planner",
        data={"agent": "planner", "step": 1},
    )
    db_session.add(event)

    step = AgentStep(
        task_id=task_uuid,
        agent_name="planner",
        step_number=1,
        status="completed",
        tokens_used=420,
        duration_ms=1800,
    )
    db_session.add(step)
    await db_session.commit()

    return str(task_uuid)


# ─── GET /tasks/{id}/events ───────────────────────────────────────────────────

async def test_get_events_returns_list_for_existing_task(async_client, seeded_task):
    response = await async_client.get(f"/tasks/{seeded_task}/events")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["event_type"] == "agent_start"
    assert body[0]["agent_name"] == "planner"
    assert "created_at" in body[0]


async def test_get_events_returns_empty_list_when_no_events(
    async_client, db_session: AsyncSession
):
    """Task exists but has no events — should return empty list."""
    task_uuid = uuid.uuid4()
    run = TaskRun(
        id=task_uuid,
        original_task="Research fintech trends in Chile.",
        status="pending",
        human_in_loop=False,
    )
    db_session.add(run)
    await db_session.commit()

    response = await async_client.get(f"/tasks/{str(task_uuid)}/events")
    assert response.status_code == 200
    assert response.json() == []


async def test_get_events_404_unknown_task(async_client):
    response = await async_client.get(f"/tasks/{uuid.uuid4()}/events")
    assert response.status_code == 404


async def test_get_events_404_invalid_uuid(async_client):
    response = await async_client.get("/tasks/not-a-valid-uuid/events")
    assert response.status_code == 404


# ─── GET /tasks/{id}/steps ────────────────────────────────────────────────────

async def test_get_steps_returns_list_for_existing_task(async_client, seeded_task):
    response = await async_client.get(f"/tasks/{seeded_task}/steps")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["agent_name"] == "planner"
    assert body[0]["tokens_used"] == 420
    assert body[0]["step_number"] == 1


async def test_get_steps_404_unknown_task(async_client):
    response = await async_client.get(f"/tasks/{uuid.uuid4()}/steps")
    assert response.status_code == 404


async def test_get_steps_returns_empty_list_when_no_steps(
    async_client, db_session: AsyncSession
):
    task_uuid = uuid.uuid4()
    run = TaskRun(
        id=task_uuid,
        original_task="Research fintech trends in Chile.",
        status="pending",
        human_in_loop=False,
    )
    db_session.add(run)
    await db_session.commit()

    response = await async_client.get(f"/tasks/{str(task_uuid)}/steps")
    assert response.status_code == 200
    assert response.json() == []
