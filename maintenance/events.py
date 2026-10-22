"""Public Server-Sent Events (SSE) protocol and durable event replay."""

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from maintenance.contracts import EventType, PublicEvent


class EventBus:
    def __init__(self, db_pool: Any = None):
        self.pool = db_pool
        self._subscribers: dict[UUID, list[asyncio.Queue[PublicEvent]]] = {}
        self._lock = asyncio.Lock()

    async def emit(
        self,
        run_id: UUID,
        sequence: int,
        event_type: EventType,
        data: dict[str, Any],
    ) -> PublicEvent:
        event = PublicEvent(
            protocol_version="maintenance/v1",
            run_id=run_id,
            sequence=sequence,
            type=event_type,
            created_at=datetime.now(timezone.utc),
            data=data,
        )

        # Persist before broadcasting
        if self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO run_events (run_id, sequence, event_type, public_payload, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (run_id, sequence) DO NOTHING
                    """,
                    run_id,
                    sequence,
                    event_type,
                    json.dumps(data),
                    event.created_at,
                )

        # Broadcast to active memory subscribers
        async with self._lock:
            queues = self._subscribers.get(run_id, [])
            for q in queues:
                await q.put(event)

        return event

    async def get_next_sequence(self, run_id: UUID) -> int:
        if self.pool:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT COALESCE(MAX(sequence), 0) + 1 AS next_seq FROM run_events WHERE run_id = $1",
                    run_id,
                )
                return row["next_seq"] if row else 1
        return 1

    async def subscribe(
        self,
        run_id: UUID,
        after_sequence: int = 0,
    ) -> AsyncIterator[str]:
        """Yields SSE-formatted lines with durable replay of past events and live streaming."""
        queue: asyncio.Queue[PublicEvent] = asyncio.Queue()

        async with self._lock:
            if run_id not in self._subscribers:
                self._subscribers[run_id] = []
            self._subscribers[run_id].append(queue)

        try:
            # 1. Replay historical events from DB after_sequence
            last_seq = after_sequence
            if self.pool:
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch(
                        """
                        SELECT sequence, event_type, public_payload, created_at
                        FROM run_events
                        WHERE run_id = $1 AND sequence > $2
                        ORDER BY sequence ASC
                        """,
                        run_id,
                        after_sequence,
                    )
                    for r in rows:
                        payload = r["public_payload"]
                        if isinstance(payload, str):
                            payload = json.loads(payload)
                        ev = PublicEvent(
                            protocol_version="maintenance/v1",
                            run_id=run_id,
                            sequence=r["sequence"],
                            type=r["event_type"],
                            created_at=r["created_at"],
                            data=payload,
                        )
                        last_seq = max(last_seq, ev.sequence)
                        yield f"id: {ev.sequence}\nevent: {ev.type}\ndata: {ev.model_dump_json()}\n\n"
                        if ev.type in {"done", "run_cancelled", "run_failed"}:
                            return

            # 2. Stream new live events
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    if event.sequence <= last_seq:
                        continue
                    last_seq = event.sequence
                    yield f"id: {event.sequence}\nevent: {event.type}\ndata: {event.model_dump_json()}\n\n"
                    if event.type in {"done", "run_cancelled", "run_failed"}:
                        break
                except asyncio.TimeoutError:
                    # Heartbeat comment to keep HTTP connection alive through proxies
                    yield ": ping\n\n"
        finally:
            async with self._lock:
                if run_id in self._subscribers and queue in self._subscribers[run_id]:
                    self._subscribers[run_id].remove(queue)
                    if not self._subscribers[run_id]:
                        del self._subscribers[run_id]
