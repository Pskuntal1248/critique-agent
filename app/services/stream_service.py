"""SSE stream service — polls agent_events table for real-time event delivery.

Replaces the previous asyncio.Queue approach.  Any number of FastAPI workers
can serve the same task's SSE stream because the source of truth is PostgreSQL,
not an in-process memory structure.
"""

import asyncio
import time
import uuid

from sqlalchemy import select

from app.core.constants import EVENT_TASK_COMPLETE, EVENT_TASK_FAILED
from app.core.logging import get_logger
from app.models.agent_event import AgentEvent
from app.models.database import AsyncSessionLocal

logger = get_logger(__name__)

_FINAL_EVENTS = frozenset({EVENT_TASK_COMPLETE, EVENT_TASK_FAILED})


async def stream_events(
    task_id: str,
    poll_interval: float = 1.0,
    timeout: float = 300.0,
):
    """Async generator — polls agent_events and yields event dicts.

    Each yielded dict has the shape ``{"event": str, "data": dict}``.
    The generator stops when:
    * a terminal event (task_complete / task_failed) is received,
    * any event with ``data["is_final"] == True`` is received, or
    * *timeout* seconds elapse with no terminal event.

    Args:
        task_id:       UUID string of the task to stream.
        poll_interval: Seconds to sleep when no new events are found.
        timeout:       Maximum total seconds before the generator exits.
    """
    last_id = 0
    task_uuid = uuid.UUID(task_id)
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AgentEvent)
                .where(AgentEvent.task_id == task_uuid)
                .where(AgentEvent.id > last_id)
                .order_by(AgentEvent.id)
            )
            new_events = result.scalars().all()

        if not new_events:
            await asyncio.sleep(poll_interval)
            continue

        for ev in new_events:
            last_id = ev.id
            yield {
                "event": ev.event_type,
                "data": {
                    **ev.data,
                    "timestamp": ev.created_at.isoformat(),
                },
            }
            # Stop as soon as we see a terminal event
            if ev.event_type in _FINAL_EVENTS or ev.data.get("is_final"):
                return

        # Got non-terminal events — loop immediately (no sleep) to drain the queue
