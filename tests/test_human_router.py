"""Tests for the human-in-the-loop approval endpoints."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def task_id() -> str:
    return str(uuid.uuid4())


# ── POST /tasks/{id}/approve ───────────────────────────────────────────────────


async def test_approve_task_success(async_client, task_id):
    with patch(
        "app.api.routers.human.approve_task",
        new=AsyncMock(return_value=True),
    ):
        response = await async_client.post(
            f"/tasks/{task_id}/approve",
            json={"decision": "approve"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["decision"] == "approve"
    assert data["status"] == "resumed"


async def test_reject_task_success(async_client, task_id):
    with patch(
        "app.api.routers.human.approve_task",
        new=AsyncMock(return_value=True),
    ):
        response = await async_client.post(
            f"/tasks/{task_id}/approve",
            json={"decision": "reject"},
        )

    assert response.status_code == 200
    assert response.json()["decision"] == "reject"


async def test_feedback_decision_with_text_success(async_client, task_id):
    with patch(
        "app.api.routers.human.approve_task",
        new=AsyncMock(return_value=True),
    ):
        response = await async_client.post(
            f"/tasks/{task_id}/approve",
            json={
                "decision": "feedback",
                "feedback": "Please add more data on regulatory environment.",
            },
        )

    assert response.status_code == 200


async def test_feedback_decision_without_text_rejected(async_client, task_id):
    """decision=feedback without feedback text must be rejected with 422."""
    with patch(
        "app.api.routers.human.approve_task",
        new=AsyncMock(return_value=True),
    ):
        response = await async_client.post(
            f"/tasks/{task_id}/approve",
            json={"decision": "feedback"},
        )

    assert response.status_code == 422


async def test_approve_not_awaiting_returns_409(async_client, task_id):
    """If no future is registered (task not paused), return 409 Conflict."""
    with patch(
        "app.api.routers.human.approve_task",
        new=AsyncMock(return_value=False),  # False → not awaiting
    ):
        response = await async_client.post(
            f"/tasks/{task_id}/approve",
            json={"decision": "approve"},
        )

    assert response.status_code == 409
    assert "awaiting" in response.json()["detail"].lower()


async def test_invalid_decision_rejected(async_client, task_id):
    """Decision must match the pattern ^(approve|reject|feedback)$."""
    response = await async_client.post(
        f"/tasks/{task_id}/approve",
        json={"decision": "maybe"},
    )
    assert response.status_code == 422
