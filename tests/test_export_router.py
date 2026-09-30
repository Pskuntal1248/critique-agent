"""Tests for GET /tasks/{id}/report.md and GET /tasks/{id}/report.json."""

from unittest.mock import AsyncMock, patch

from tests.conftest import make_task_run

TASK_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
SAMPLE_REPORT = "# Fintech Report\n\nExecutive summary here.\n\n## Sources\n\n1. [Example](https://example.com)"


# ─── Markdown export ─────────────────────────────────────────────────────────

async def test_export_md_returns_200(async_client):
    run = make_task_run(task_id=TASK_ID, status="complete")
    run.final_report = SAMPLE_REPORT

    with patch("app.api.routers.export.get_task", new=AsyncMock(return_value=run)):
        response = await async_client.get(f"/tasks/{TASK_ID}/report.md")

    assert response.status_code == 200
    assert "text/markdown" in response.headers["content-type"]
    assert "# Fintech Report" in response.text
    assert "attachment" in response.headers.get("content-disposition", "")


async def test_export_md_404_task_not_found(async_client):
    with patch("app.api.routers.export.get_task", new=AsyncMock(return_value=None)):
        response = await async_client.get(f"/tasks/{TASK_ID}/report.md")
    assert response.status_code == 404


async def test_export_md_404_no_report(async_client):
    run = make_task_run(task_id=TASK_ID, status="running")
    run.final_report = None

    with patch("app.api.routers.export.get_task", new=AsyncMock(return_value=run)):
        response = await async_client.get(f"/tasks/{TASK_ID}/report.md")
    assert response.status_code == 404


async def test_export_md_404_invalid_uuid(async_client):
    response = await async_client.get("/tasks/not-a-uuid/report.md")
    assert response.status_code == 404


# ─── JSON export ──────────────────────────────────────────────────────────────

async def test_export_json_returns_200(async_client):
    run = make_task_run(task_id=TASK_ID, status="complete")
    run.final_report = SAMPLE_REPORT

    with patch("app.api.routers.export.get_task", new=AsyncMock(return_value=run)):
        response = await async_client.get(f"/tasks/{TASK_ID}/report.json")

    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == TASK_ID
    assert body["status"] == "complete"
    assert body["final_report"] == SAMPLE_REPORT
    assert "total_prompt_tokens" in body
    assert "estimated_cost_usd" in body


async def test_export_json_404_task_not_found(async_client):
    with patch("app.api.routers.export.get_task", new=AsyncMock(return_value=None)):
        response = await async_client.get(f"/tasks/{TASK_ID}/report.json")
    assert response.status_code == 404


async def test_export_json_404_no_report(async_client):
    run = make_task_run(task_id=TASK_ID, status="running")
    run.final_report = None

    with patch("app.api.routers.export.get_task", new=AsyncMock(return_value=run)):
        response = await async_client.get(f"/tasks/{TASK_ID}/report.json")
    assert response.status_code == 404
