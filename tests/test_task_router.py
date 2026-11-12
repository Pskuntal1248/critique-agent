"""Tests for POST /tasks and GET /tasks/{task_id} endpoints."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

VALID_TASK = "Research the fintech market in Chile and identify top 3 opportunities"
SHORT_TASK = "too short"


@pytest.fixture
def task_id() -> str:
    return str(uuid.uuid4())


# ── POST /tasks ────────────────────────────────────────────────────────────────


async def test_create_task_success(async_client, task_id):
    from tests.conftest import make_task_run

    fake_run = make_task_run(task_id=task_id, task=VALID_TASK)

    with patch(
        "app.api.routers.tasks.create_task",
        new=AsyncMock(return_value=fake_run),
    ):
        response = await async_client.post(
            "/tasks",
            json={"task": VALID_TASK},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["status"] == "pending"
    assert data["original_task"] == VALID_TASK


async def test_create_task_with_human_in_loop(async_client, task_id):
    from tests.conftest import make_task_run

    fake_run = make_task_run(task_id=task_id, human_in_loop=True)

    with patch(
        "app.api.routers.tasks.create_task",
        new=AsyncMock(return_value=fake_run),
    ):
        response = await async_client.post(
            "/tasks",
            json={"task": VALID_TASK, "human_in_loop": True},
        )

    assert response.status_code == 200
    assert response.json()["human_in_loop"] is True


async def test_create_task_too_short_rejected(async_client):
    """Task with fewer than 10 chars should fail Pydantic validation."""
    response = await async_client.post("/tasks", json={"task": "short"})
    assert response.status_code == 422


async def test_create_task_missing_body_rejected(async_client):
    response = await async_client.post("/tasks", json={})
    assert response.status_code == 422


# ── GET /tasks/{task_id} ───────────────────────────────────────────────────────


async def test_get_task_success(async_client, task_id):
    from tests.conftest import make_task_run

    fake_run = make_task_run(task_id=task_id, status="complete", task=VALID_TASK)
    fake_run.final_report = "# Final Report\n\nGreat findings."

    with patch(
        "app.api.routers.tasks.get_task",
        new=AsyncMock(return_value=fake_run),
    ):
        response = await async_client.get(f"/tasks/{task_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["status"] == "complete"
    assert data["final_report"] == "# Final Report\n\nGreat findings."


async def test_get_task_not_found(async_client):
    with patch(
        "app.api.routers.tasks.get_task",
        new=AsyncMock(return_value=None),
    ):
        response = await async_client.get(f"/tasks/{uuid.uuid4()}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ── Auth ───────────────────────────────────────────────────────────────────────


async def test_auth_required_when_api_key_set(async_client):
    """When API_KEY is configured, requests without it get 401."""
    with patch("app.core.auth.settings") as mock_settings:
        mock_settings.auth_enabled = True
        mock_settings.api_key = "secret-key"

        response = await async_client.post(
            "/tasks",
            json={"task": VALID_TASK},
            # no X-API-Key header
        )

    assert response.status_code == 401


async def test_auth_passes_with_correct_key(async_client, task_id):
    from tests.conftest import make_task_run

    fake_run = make_task_run(task_id=task_id)

    with (
        patch("app.core.auth.settings") as mock_settings,
        patch(
            "app.api.routers.tasks.create_task",
            new=AsyncMock(return_value=fake_run),
        ),
    ):
        mock_settings.auth_enabled = True
        mock_settings.api_key = "secret-key"

        response = await async_client.post(
            "/tasks",
            json={"task": VALID_TASK},
            headers={"X-API-Key": "secret-key"},
        )

    assert response.status_code == 200


# ── GET /tasks (list) ──────────────────────────────────────────────────────────


async def test_list_tasks_returns_summaries(async_client):
    from tests.conftest import make_task_run

    runs = [
        make_task_run(status="complete", task=VALID_TASK),
        make_task_run(status="failed", task=VALID_TASK),
    ]

    with patch(
        "app.api.routers.tasks.list_tasks",
        new=AsyncMock(return_value=runs),
    ) as mocked:
        response = await async_client.get("/tasks?limit=2")

    assert response.status_code == 200
    data = response.json()
    assert [r["status"] for r in data] == ["complete", "failed"]
    assert "final_report" not in data[0]
    assert mocked.await_args.kwargs["limit"] == 2


async def test_list_tasks_rejects_bad_limit(async_client):
    response = await async_client.get("/tasks?limit=0")
    assert response.status_code == 422


def test_response_datetimes_are_utc_aware():
    from datetime import UTC, datetime, timedelta, timezone

    from app.api.schemas.task import AgentStepResponse

    base = dict(id=1, agent_name="a", step_number=1, status="completed",
                output_summary=None, tokens_used=0, duration_ms=None, error=None)
    naive = AgentStepResponse(**base, created_at=datetime(2026, 1, 1, 12, 0))
    assert naive.created_at.utcoffset() == timedelta(0)
    assert naive.model_dump_json().count("Z") == 1 or "+00:00" in naive.model_dump_json()
    ist = timezone(timedelta(hours=5, minutes=30))
    aware = AgentStepResponse(**base, created_at=datetime(2026, 1, 1, 12, 0, tzinfo=ist))
    assert aware.created_at.utcoffset() == timedelta(hours=5, minutes=30)  # offset preserved, not overwritten
    assert aware.created_at.astimezone(UTC).hour == 6
