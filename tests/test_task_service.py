"""Tests for task_service — create tasks, approve, and cancel."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.task_service import approve_task, cancel_task, create_task

_CELERY_ID = str(uuid.uuid4())


def _mock_celery():
    """Return a mock run_graph whose .delay() returns a result with a real UUID .id."""
    mock = MagicMock()
    result = MagicMock()
    result.id = _CELERY_ID
    mock.delay.return_value = result
    return mock

VALID_TASK = (
    "Research the fintech market in Chile and identify the top 3 opportunities for 2025."
)


# ─── create_task ──────────────────────────────────────────────────────────────

async def test_create_task_inserts_db_row(db_session: AsyncSession):
    """create_task persists a TaskRun and returns it."""
    with patch("app.services.task_service.run_graph", new=_mock_celery()):
        run = await create_task(db_session, VALID_TASK)

    assert run.id is not None
    assert run.original_task == VALID_TASK
    assert run.status == "pending"


async def test_create_task_enqueues_celery_with_correct_args(db_session: AsyncSession):
    """run_graph.delay must be called with (task_id, task_text, human_in_loop)."""
    with patch("app.services.task_service.run_graph", new=_mock_celery()) as mock_celery:
        run = await create_task(db_session, VALID_TASK, human_in_loop=False)

    mock_celery.delay.assert_called_once()
    args = mock_celery.delay.call_args[0]
    assert args[0] == str(run.id)
    assert args[1] == VALID_TASK
    assert args[2] is False


async def test_create_task_human_in_loop_true(db_session: AsyncSession):
    """human_in_loop=True is stored on the run and forwarded to Celery."""
    with patch("app.services.task_service.run_graph", new=_mock_celery()) as mock_celery:
        run = await create_task(db_session, VALID_TASK, human_in_loop=True)

    assert run.human_in_loop is True
    args = mock_celery.delay.call_args[0]
    assert args[2] is True


async def test_create_task_uses_settings_default(db_session: AsyncSession):
    """When human_in_loop is None the setting default is used."""
    with patch("app.services.task_service.run_graph", new=_mock_celery()):
        with patch("app.services.task_service.settings") as mock_settings:
            mock_settings.human_in_loop = False
            run = await create_task(db_session, VALID_TASK)

    assert run.human_in_loop is False


# ─── approve_task ─────────────────────────────────────────────────────────────

def _mock_db_with_run(run):
    """Return a mock AsyncSessionLocal context manager backed by *run*."""
    mock_db = MagicMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    mock_db.scalar = AsyncMock(return_value=run)
    mock_db.commit = AsyncMock()
    return mock_db


async def test_approve_task_writes_decision():
    """approve_task stores the decision and returns True."""
    task_id = str(uuid.uuid4())
    mock_run = MagicMock()
    mock_run.status = "awaiting_approval"
    mock_run.human_decision = None
    mock_run.human_feedback = None

    mock_db = _mock_db_with_run(mock_run)

    with patch("app.services.task_service.AsyncSessionLocal", return_value=mock_db):
        result = await approve_task(task_id, "approve")

    assert result is True
    assert mock_run.human_decision == "approve"
    mock_db.commit.assert_called_once()


async def test_approve_task_stores_feedback():
    """approve_task stores the feedback text when provided."""
    task_id = str(uuid.uuid4())
    mock_run = MagicMock()
    mock_run.status = "awaiting_approval"

    mock_db = _mock_db_with_run(mock_run)

    with patch("app.services.task_service.AsyncSessionLocal", return_value=mock_db):
        await approve_task(task_id, "feedback", feedback="Add Nubank competitor analysis.")

    assert mock_run.human_feedback == "Add Nubank competitor analysis."
    assert mock_run.human_decision == "feedback"


async def test_approve_task_returns_false_when_not_awaiting():
    """approve_task returns False (no DB write) when status != awaiting_approval."""
    task_id = str(uuid.uuid4())
    mock_run = MagicMock()
    mock_run.status = "running"

    mock_db = _mock_db_with_run(mock_run)

    with patch("app.services.task_service.AsyncSessionLocal", return_value=mock_db):
        result = await approve_task(task_id, "approve")

    assert result is False
    mock_db.commit.assert_not_called()


async def test_approve_task_returns_false_when_not_found():
    """approve_task returns False when the task_id doesn't exist."""
    task_id = str(uuid.uuid4())
    mock_db = _mock_db_with_run(None)  # DB returns None

    with patch("app.services.task_service.AsyncSessionLocal", return_value=mock_db):
        result = await approve_task(task_id, "approve")

    assert result is False
    mock_db.commit.assert_not_called()


async def test_approve_task_reject_decision():
    """reject decision is stored correctly."""
    task_id = str(uuid.uuid4())
    mock_run = MagicMock()
    mock_run.status = "awaiting_approval"

    mock_db = _mock_db_with_run(mock_run)

    with patch("app.services.task_service.AsyncSessionLocal", return_value=mock_db):
        result = await approve_task(task_id, "reject")

    assert result is True
    assert mock_run.human_decision == "reject"


# ─── cancel_task ──────────────────────────────────────────────────────────────

async def test_cancel_task_returns_cancelled():
    """cancel_task returns 'cancelled' for a running task."""
    task_id = str(uuid.uuid4())
    mock_run = MagicMock()
    mock_run.status = "running"
    mock_run.celery_task_id = None  # no Celery job to revoke

    mock_db = _mock_db_with_run(mock_run)

    with patch("app.services.task_service.AsyncSessionLocal", return_value=mock_db):
        result = await cancel_task(task_id)

    assert result == "cancelled"
    assert mock_run.status == "cancelled"
    mock_db.commit.assert_called_once()


async def test_cancel_task_returns_not_found():
    """cancel_task returns 'not_found' when task doesn't exist."""
    task_id = str(uuid.uuid4())
    mock_db = _mock_db_with_run(None)

    with patch("app.services.task_service.AsyncSessionLocal", return_value=mock_db):
        result = await cancel_task(task_id)

    assert result == "not_found"
    mock_db.commit.assert_not_called()


async def test_cancel_task_returns_already_terminal():
    """cancel_task returns 'already_terminal' when task is already complete."""
    task_id = str(uuid.uuid4())
    mock_run = MagicMock()
    mock_run.status = "complete"

    mock_db = _mock_db_with_run(mock_run)

    with patch("app.services.task_service.AsyncSessionLocal", return_value=mock_db):
        result = await cancel_task(task_id)

    assert result == "already_terminal"
    mock_db.commit.assert_not_called()


async def test_cancel_task_already_terminal_for_all_statuses():
    """All terminal statuses (complete/failed/cancelled/best_effort) return already_terminal."""
    for terminal_status in ("complete", "failed", "cancelled", "best_effort"):
        task_id = str(uuid.uuid4())
        mock_run = MagicMock()
        mock_run.status = terminal_status
        mock_db = _mock_db_with_run(mock_run)

        with patch("app.services.task_service.AsyncSessionLocal", return_value=mock_db):
            result = await cancel_task(task_id)

        assert result == "already_terminal", f"Expected 'already_terminal' for status={terminal_status}"
