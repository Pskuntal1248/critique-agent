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


# ─── GET /tasks/{id}/review ───────────────────────────────────────────────────

@pytest.fixture
async def review_task(db_session: AsyncSession):
    task_uuid = uuid.uuid4()
    db_session.add(TaskRun(id=task_uuid, original_task="Compare two tools for a team.",
                           status="awaiting_approval", human_in_loop=True, revision_count=1))
    await db_session.commit()
    rows = [
        ("researcher", 1, {"research_results": [{"subtask": "a", "summary": "s", "sources": [
            {"url": "https://example.com/a", "title": "Source A", "content": "SECRET-BODY"},
            {"url": "javascript:alert(1)", "title": "bad"},
            {"url": "https://example.com/a", "title": "dup"}]}],
            "api_key": "sk-LEAK"}),
        ("analyst", 2, {"analysis": "first draft", "status": "analyzing"}),
        ("critic", 3, {"critic_score": 0.5, "critic_approved": False, "critic_feedback": "add detail"}),
        ("analyst", 4, {"analysis": "# Final draft\n\nBody text"}),
        ("critic", 5, {"critic_score": 0.7, "critic_approved": True, "critic_feedback": ""}),
    ]
    for name, n, data in rows:
        db_session.add(AgentStep(task_id=task_uuid, agent_name=name, step_number=n,
                                 status="completed", output_data=data))
    await db_session.commit()
    return str(task_uuid)


async def test_review_returns_latest_full_draft_notes_and_sources(async_client, review_task):
    r = await async_client.get(f"/tasks/{review_task}/review")
    assert r.status_code == 200
    body = r.json()
    assert body["analysis"] == "# Final draft\n\nBody text"
    assert [n["score"] for n in body["critic_notes"]] == [0.5, 0.7]
    assert body["critic_notes"][0]["feedback"] == "add detail"
    assert body["critic_notes"][1]["approved"] is True
    assert body["sources"] == [{"title": "Source A", "url": "https://example.com/a"}]
    assert body["revision_count"] == 1


async def test_review_does_not_expose_other_step_data(async_client, review_task):
    text = (await async_client.get(f"/tasks/{review_task}/review")).text
    assert "sk-LEAK" not in text and "SECRET-BODY" not in text and "javascript:" not in text


async def test_review_404_for_unknown_task(async_client):
    r = await async_client.get(f"/tasks/{uuid.uuid4()}/review")
    assert r.status_code == 404
