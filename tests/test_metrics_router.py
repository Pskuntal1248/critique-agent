"""Tests for GET /metrics endpoint."""

from unittest.mock import AsyncMock, patch

import pytest

FAKE_METRICS = {
    "period_hours": 24,
    "runs_total": 10,
    "runs_successful": 8,
    "success_rate_pct": 80.0,
    "avg_duration_ms": 4200,
    "p95_duration_ms": 8100,
    "avg_tokens_per_run": 1500,
    "avg_revisions": 1.2,
    "agent_avg_latency_ms": {"planner": 320, "researcher": 1800, "analyst": 950},
}


async def test_metrics_returns_200(async_client):
    with patch(
        "app.api.routers.metrics.get_metrics",
        new=AsyncMock(return_value=FAKE_METRICS),
    ):
        response = await async_client.get("/metrics")

    assert response.status_code == 200


async def test_metrics_response_shape(async_client):
    with patch(
        "app.api.routers.metrics.get_metrics",
        new=AsyncMock(return_value=FAKE_METRICS),
    ):
        response = await async_client.get("/metrics")

    data = response.json()
    assert data["runs_total"] == 10
    assert data["runs_successful"] == 8
    assert data["success_rate_pct"] == 80.0
    assert data["avg_duration_ms"] == 4200
    assert data["p95_duration_ms"] == 8100
    assert data["avg_tokens_per_run"] == 1500
    assert data["avg_revisions"] == pytest.approx(1.2)
    assert "planner" in data["agent_avg_latency_ms"]


async def test_metrics_custom_hours_parameter(async_client):
    with patch(
        "app.api.routers.metrics.get_metrics",
        new=AsyncMock(return_value={**FAKE_METRICS, "period_hours": 48}),
    ) as mock_get:
        response = await async_client.get("/metrics?hours=48")

    assert response.status_code == 200
    assert response.json()["period_hours"] == 48
    # Verify the service was called with hours=48
    mock_get.assert_called_once()
    _, kwargs = mock_get.call_args
    assert kwargs.get("hours") == 48 or mock_get.call_args[0][1] == 48


async def test_metrics_hours_out_of_range_rejected(async_client):
    """hours must be 1–168; outside range → 422."""
    response = await async_client.get("/metrics?hours=0")
    assert response.status_code == 422

    response = await async_client.get("/metrics?hours=999")
    assert response.status_code == 422


async def test_metrics_empty_result(async_client):
    empty = {
        "period_hours": 24,
        "runs_total": 0,
        "runs_successful": 0,
        "success_rate_pct": 0.0,
        "avg_duration_ms": 0,
        "p95_duration_ms": 0,
        "avg_tokens_per_run": 0,
        "avg_revisions": 0.0,
        "agent_avg_latency_ms": {},
    }
    with patch(
        "app.api.routers.metrics.get_metrics",
        new=AsyncMock(return_value=empty),
    ):
        response = await async_client.get("/metrics")

    assert response.status_code == 200
    assert response.json()["runs_total"] == 0
    assert response.json()["agent_avg_latency_ms"] == {}
