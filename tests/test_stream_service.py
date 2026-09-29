"""Tests for the DB-polling SSE stream service."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from app.services.stream_service import stream_events

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_agent_event(id: int, event_type: str, data: dict | None = None) -> MagicMock:
    """Build a mock AgentEvent ORM object."""
    ev = MagicMock()
    ev.id = id
    ev.event_type = event_type
    ev.data = data or {}
    ev.created_at = datetime.now(UTC)
    return ev


def _db_factory(batches: list[list]):
    """
    Return a mock AsyncSessionLocal context manager that yields successive
    *batches* of events.  Once all batches are exhausted the last one repeats.
    """
    state = {"call": 0}

    class _MockDB:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            pass

        async def execute(self, _query):
            idx = min(state["call"], len(batches) - 1)
            state["call"] += 1
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = batches[idx]
            return mock_result

    def factory():
        return _MockDB()

    return factory


# ─── Tests ────────────────────────────────────────────────────────────────────

async def test_stream_events_yields_all_events_in_order():
    """Events returned by DB query are yielded in insertion order."""
    ev1 = _make_agent_event(1, "agent_start", {"agent": "planner", "step": 1})
    ev2 = _make_agent_event(2, "agent_complete", {"agent": "planner"})
    ev3 = _make_agent_event(3, "task_complete", {"status": "complete", "is_final": True})

    factory = _db_factory([[ev1, ev2, ev3]])

    with patch("app.services.stream_service.AsyncSessionLocal", factory):
        received = []
        async for event in stream_events("00000000-0000-0000-0000-000000000001", poll_interval=0.01, timeout=5.0):
            received.append(event)

    assert len(received) == 3
    assert received[0]["event"] == "agent_start"
    assert received[0]["data"]["agent"] == "planner"
    assert received[1]["event"] == "agent_complete"
    assert received[2]["event"] == "task_complete"


async def test_stream_events_stops_on_task_complete():
    """Generator stops immediately after task_complete."""
    ev1 = _make_agent_event(1, "agent_start", {"agent": "planner"})
    ev2 = _make_agent_event(2, "task_complete", {"status": "complete"})
    ev3 = _make_agent_event(3, "agent_start", {"agent": "writer"})  # should never arrive

    factory = _db_factory([[ev1, ev2, ev3]])

    with patch("app.services.stream_service.AsyncSessionLocal", factory):
        received = []
        async for event in stream_events("00000000-0000-0000-0000-000000000002", poll_interval=0.01, timeout=5.0):
            received.append(event)

    # ev3 is after the terminal event — must not be yielded
    assert len(received) == 2
    assert received[-1]["event"] == "task_complete"


async def test_stream_events_stops_on_task_failed():
    """Generator stops immediately after task_failed."""
    ev = _make_agent_event(1, "task_failed", {"error": "llm_timeout"})

    factory = _db_factory([[ev]])

    with patch("app.services.stream_service.AsyncSessionLocal", factory):
        received = []
        async for event in stream_events("00000000-0000-0000-0000-000000000003", poll_interval=0.01, timeout=5.0):
            received.append(event)

    assert len(received) == 1
    assert received[0]["event"] == "task_failed"


async def test_stream_events_stops_on_is_final_flag():
    """Any event with is_final=True terminates the stream."""
    ev = _make_agent_event(1, "task_complete", {"status": "complete", "is_final": True})

    factory = _db_factory([[ev]])

    with patch("app.services.stream_service.AsyncSessionLocal", factory):
        received = []
        async for event in stream_events("00000000-0000-0000-0000-000000000004", poll_interval=0.01, timeout=5.0):
            received.append(event)

    assert len(received) == 1


async def test_stream_events_polls_after_empty_batch():
    """Empty poll → events arrive on second poll → yielded correctly."""
    ev = _make_agent_event(1, "task_complete", {"is_final": True})
    # First poll: nothing.  Second poll: terminal event.
    factory = _db_factory([[], [ev]])

    with patch("app.services.stream_service.AsyncSessionLocal", factory):
        received = []
        async for event in stream_events("00000000-0000-0000-0000-000000000005", poll_interval=0.01, timeout=5.0):
            received.append(event)

    assert len(received) == 1
    assert received[0]["event"] == "task_complete"


async def test_stream_events_timeout_yields_nothing():
    """When no events arrive within timeout the generator exits without error."""
    factory = _db_factory([[]])  # always empty

    with patch("app.services.stream_service.AsyncSessionLocal", factory):
        received = []
        async for event in stream_events("00000000-0000-0000-0000-000000000006", poll_interval=0.01, timeout=0.05):
            received.append(event)

    assert received == []


async def test_stream_events_timestamp_injected():
    """Each yielded event dict must contain a 'timestamp' key in data."""
    ev = _make_agent_event(1, "task_complete", {"is_final": True})
    factory = _db_factory([[ev]])

    with patch("app.services.stream_service.AsyncSessionLocal", factory):
        received = []
        async for event in stream_events("00000000-0000-0000-0000-000000000007", poll_interval=0.01, timeout=5.0):
            received.append(event)

    assert "timestamp" in received[0]["data"]
    assert "T" in received[0]["data"]["timestamp"]  # ISO-8601 marker


async def test_stream_events_tracks_last_id_across_polls():
    """Each successive poll uses the highest seen id — events are not repeated."""
    ev1 = _make_agent_event(10, "agent_start", {"agent": "planner"})
    ev2 = _make_agent_event(20, "task_complete", {"is_final": True})
    # Two separate polls: first yields ev1, second yields ev2
    factory = _db_factory([[ev1], [ev2]])

    with patch("app.services.stream_service.AsyncSessionLocal", factory):
        received = []
        async for event in stream_events("00000000-0000-0000-0000-000000000008", poll_interval=0.001, timeout=5.0):
            received.append(event)

    assert len(received) == 2
    assert received[0]["event"] == "agent_start"
    assert received[1]["event"] == "task_complete"
