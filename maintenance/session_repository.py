"""Asyncpg-backed transactional session, run, evidence and workflow repository."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from maintenance.contracts import (
    AnswerEnvelope,
    BoardItem,
    HypothesisEnvelope,
    Mode,
    SessionSnapshot,
)


class SessionRepository:
    def __init__(self, pool: Any):
        self.pool = pool

    async def create_session(
        self,
        owner_id: UUID,
        domain: str = "aviation",
        title: str = "New investigation",
        aircraft_profile: dict[str, Any] | None = None,
    ) -> SessionSnapshot:
        session_id = uuid4()
        profile_data = aircraft_profile or {}
        board_data = {"known": [], "reported": [], "missing": []}

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sessions (session_id, owner_id, title, domain, status, state_revision, aircraft_profile, board)
                VALUES ($1, $2, $3, $4, 'active', 0, $5::jsonb, $6::jsonb)
                """,
                session_id,
                owner_id,
                title,
                domain,
                profile_data,
                board_data,
            )

        return SessionSnapshot(
            session_id=session_id,
            domain=domain,
            title=title,
            state_revision=0,
            aircraft_profile=aircraft_profile or {},
            board=[],
            messages=[],
            answers=[],
            active_run_id=None,
        )

    async def list_sessions(
        self,
        owner_id: UUID,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT session_id, domain, title, status, state_revision, created_at, updated_at
                FROM sessions
                WHERE owner_id = $1 AND status != 'deleted'
                ORDER BY updated_at DESC
                LIMIT $2
                """,
                owner_id,
                limit,
            )
            return [
                {
                    "session_id": str(r["session_id"]),
                    "domain": r["domain"],
                    "title": r["title"],
                    "status": r["status"],
                    "state_revision": r["state_revision"],
                    "created_at": r["created_at"].isoformat(),
                    "updated_at": r["updated_at"].isoformat(),
                }
                for r in rows
            ]

    async def get_session(
        self,
        session_id: UUID,
        owner_id: UUID,
    ) -> SessionSnapshot | None:
        async with self.pool.acquire() as conn:
            s_row = await conn.fetchrow(
                """
                SELECT session_id, domain, title, status, state_revision, aircraft_profile, board
                FROM sessions
                WHERE session_id = $1 AND owner_id = $2 AND status != 'deleted'
                """,
                session_id,
                owner_id,
            )
            if not s_row:
                return None

            # Fetch messages
            m_rows = await conn.fetch(
                """
                SELECT message_id, sequence, role, source_type, content, created_at
                FROM messages
                WHERE session_id = $1
                ORDER BY sequence ASC
                """,
                session_id,
            )
            messages = [
                {
                    "message_id": str(r["message_id"]),
                    "sequence": r["sequence"],
                    "role": r["role"],
                    "source_type": r["source_type"],
                    "content": json.loads(r["content"]) if isinstance(r["content"], str) else r["content"],
                    "created_at": r["created_at"].isoformat(),
                }
                for r in m_rows
            ]

            # Fetch released answers
            ans_rows = await conn.fetch(
                """
                SELECT a.answer_id, a.run_id, a.source_mode, a.envelope
                FROM answers a
                JOIN runs r ON a.run_id = r.run_id
                WHERE r.session_id = $1
                ORDER BY a.released_at ASC
                """,
                session_id,
            )
            answers: list[AnswerEnvelope | HypothesisEnvelope] = []
            for r in ans_rows:
                env = r["envelope"]
                if isinstance(env, str):
                    env = json.loads(env)
                if r["source_mode"] == "HYPOTHESIS":
                    answers.append(HypothesisEnvelope.model_validate(env))
                else:
                    answers.append(AnswerEnvelope.model_validate(env))

            # Fetch active run if any
            active_row = await conn.fetchrow(
                """
                SELECT run_id FROM runs
                WHERE session_id = $1 AND status IN ('queued', 'running', 'validating')
                LIMIT 1
                """,
                session_id,
            )
            active_run_id = active_row["run_id"] if active_row else None

            # Parse board items
            raw_board = s_row["board"]
            if isinstance(raw_board, str):
                raw_board = json.loads(raw_board)

            board_items: list[BoardItem] = []
            if isinstance(raw_board, list):
                board_items = [BoardItem.model_validate(b) for b in raw_board]
            elif isinstance(raw_board, dict):
                # May be {"known": [...], "reported": [...], "missing": [...]}
                for col in ["known", "reported", "missing"]:
                    for it in raw_board.get(col, []):
                        if isinstance(it, dict):
                            board_items.append(BoardItem.model_validate(it))

            profile = s_row["aircraft_profile"]
            if isinstance(profile, str):
                profile = json.loads(profile)

            return SessionSnapshot(
                session_id=s_row["session_id"],
                domain=s_row["domain"],
                title=s_row["title"],
                state_revision=s_row["state_revision"],
                aircraft_profile=profile or {},
                board=board_items,
                messages=messages,
                answers=answers,
                active_run_id=active_run_id,
            )

    async def update_session_profile(
        self,
        session_id: UUID,
        owner_id: UUID,
        expected_revision: int,
        aircraft_profile: dict[str, Any] | None = None,
        title: str | None = None,
    ) -> int:
        """Updates aircraft profile or title optimistically advancing state revision."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT state_revision FROM sessions WHERE session_id = $1 AND owner_id = $2 FOR UPDATE",
                    session_id,
                    owner_id,
                )
                if not row:
                    raise LookupError("session_not_found")
                if row["state_revision"] != expected_revision:
                    raise ValueError("state_revision_conflict")

                new_rev = expected_revision + 1
                updates = ["state_revision = $3", "updated_at = now()"]
                params: list[Any] = [session_id, owner_id, new_rev]

                if aircraft_profile is not None:
                    params.append(aircraft_profile)
                    updates.append(f"aircraft_profile = ${len(params)}::jsonb")
                if title is not None:
                    params.append(title)
                    updates.append(f"title = ${len(params)}")

                sql = f"UPDATE sessions SET {', '.join(updates)} WHERE session_id = $1 AND owner_id = $2"
                await conn.execute(sql, *params)
                return new_rev

    async def save_model_messages(
        self,
        run_id: UUID,
        turn_index: int,
        messages: list[dict[str, Any]],
        provider: str,
        adapter_version: str = "openai/v1",
    ) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO model_messages (run_id, turn_index, serialized_messages, adapter_version, provider)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (run_id, turn_index) DO UPDATE
                SET serialized_messages = EXCLUDED.serialized_messages,
                    adapter_version = EXCLUDED.adapter_version,
                    provider = EXCLUDED.provider
                """,
                run_id,
                turn_index,
                messages,
                adapter_version,
                provider,
            )

    async def delete_session(self, session_id: UUID, owner_id: UUID) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM sessions WHERE session_id = $1 AND owner_id = $2",
                session_id,
                owner_id,
            )
            return "DELETE 1" in result

    async def create_run(
        self,
        session_id: UUID,
        owner_id: UUID,
        mode: Mode,
        idempotency_key: UUID,
        request_text: str,
        expected_revision: int,
        corpus_ids: list[UUID],
        prompt_version: str = "v1.0",
        model_id: str = "deepseek-flash",
        parent_answer_id: UUID | None = None,
    ) -> tuple[UUID, bool]:
        """Creates a run or returns existing run for matching idempotency key.

        Returns (run_id, is_new). Raises ValueError on revision or idempotency conflict.
        """
        req_hash = hashlib.sha256(request_text.encode("utf-8")).hexdigest()

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Verify session ownership & current state revision
                s_row = await conn.fetchrow(
                    "SELECT state_revision FROM sessions WHERE session_id = $1 AND owner_id = $2 FOR UPDATE",
                    session_id,
                    owner_id,
                )
                if not s_row:
                    raise LookupError("session_not_found")
                if s_row["state_revision"] != expected_revision:
                    raise ValueError(f"revision_conflict: expected {expected_revision} got {s_row['state_revision']}")

                # Check if idempotency key already exists for this session
                existing = await conn.fetchrow(
                    "SELECT run_id, request_hash FROM runs WHERE session_id = $1 AND idempotency_key = $2",
                    session_id,
                    idempotency_key,
                )
                if existing:
                    if existing["request_hash"] == req_hash:
                        return existing["run_id"], False
                    raise ValueError("idempotency_payload_mismatch")

                # Check if there is already a live run
                live = await conn.fetchrow(
                    "SELECT run_id FROM runs WHERE session_id = $1 AND status IN ('queued', 'running', 'validating')",
                    session_id,
                )
                if live:
                    raise ValueError("concurrent_run_in_progress")

                run_id = uuid4()
                lease_expires = datetime.now(timezone.utc) + timedelta(seconds=30)
                await conn.execute(
                    """
                    INSERT INTO runs (
                        run_id, session_id, parent_answer_id, mode, idempotency_key, request_hash,
                        state_revision, corpus_ids, prompt_version, model_id, status, lease_expires_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10, 'queued', $11
                    )
                    """,
                    run_id,
                    session_id,
                    parent_answer_id,
                    mode,
                    idempotency_key,
                    req_hash,
                    expected_revision,
                    [str(cid) for cid in corpus_ids],
                    prompt_version,
                    model_id,
                    lease_expires,
                )

                # Append user message to messages table
                seq_row = await conn.fetchrow(
                    "SELECT COALESCE(MAX(sequence), 0) + 1 AS next_seq FROM messages WHERE session_id = $1",
                    session_id,
                )
                next_seq = seq_row["next_seq"]
                await conn.execute(
                    """
                    INSERT INTO messages (message_id, session_id, run_id, sequence, role, source_type, content)
                    VALUES ($1, $2, $3, $4, 'user', 'user_input', $5::jsonb)
                    """,
                    uuid4(),
                    session_id,
                    run_id,
                    next_seq,
                    {"text": request_text},
                )

                return run_id, True

    async def cancel_run(self, run_id: UUID, owner_id: UUID) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE runs SET cancel_requested_at = now()
                WHERE run_id = $1 AND session_id IN (SELECT session_id FROM sessions WHERE owner_id = $2)
                AND status IN ('queued', 'running', 'validating')
                """,
                run_id,
                owner_id,
            )
            return "UPDATE 1" in result

    async def get_run_owner(self, run_id: UUID) -> UUID | None:
        """Returns the owner_id of the session associated with the run, or None if run not found."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT s.owner_id
                FROM runs r
                JOIN sessions s ON s.session_id = r.session_id
                WHERE r.run_id = $1
                """,
                run_id,
            )
            return row["owner_id"] if row else None

    async def save_evidence_snapshots(
        self,
        run_id: UUID,
        snapshots: list[dict[str, Any]],
    ) -> None:
        if not snapshots:
            return
        async with self.pool.acquire() as conn:
            for s in snapshots:
                sha = s.get("text_sha256") or s.get("source_sha256")
                if not sha:
                    sha = hashlib.sha256(s["raw_text"].encode("utf-8")).hexdigest()
                await conn.execute(
                    """
                    INSERT INTO evidence_snapshots (evidence_id, run_id, corpus_id, record_id, field, raw_text, text_sha256)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (run_id, corpus_id, record_id, field) DO NOTHING
                    """,
                    s["evidence_id"],
                    run_id,
                    s["corpus_id"],
                    s["record_id"],
                    s["field"],
                    s["raw_text"],
                    sha,
                )

    async def commit_answer_and_state(
        self,
        run_id: UUID,
        session_id: UUID,
        answer: AnswerEnvelope | HypothesisEnvelope,
        validation_report: dict[str, Any],
        new_board_items: list[BoardItem],
    ) -> int:
        """Transactionally commits released answer, claim supports, board items, and advances session revision."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # 1. Insert into answers
                answer_id = answer.answer_id
                mode_str = getattr(answer, "mode", "EVIDENCE")
                await conn.execute(
                    """
                    INSERT INTO answers (answer_id, run_id, source_mode, envelope, validation_report)
                    VALUES ($1, $2, $3, $4::jsonb, $5::jsonb)
                    """,
                    answer_id,
                    run_id,
                    mode_str,
                    answer.model_dump(mode="json"),
                    validation_report,
                )

                # 2. Insert claim supports if evidence answer
                if isinstance(answer, AnswerEnvelope):
                    for claim in answer.claims:
                        for idx, sup in enumerate(claim.supports):
                            if getattr(sup, "kind", "") == "log_span":
                                await conn.execute(
                                    """
                                    INSERT INTO claim_supports (
                                        answer_id, claim_id, support_index, kind, evidence_id,
                                        span_start, span_end, quote
                                    ) VALUES ($1, $2, $3, 'log_span', $4, $5, $6, $7)
                                    """,
                                    answer_id,
                                    claim.claim_id,
                                    idx,
                                    sup.evidence_id,
                                    sup.start,
                                    sup.end,
                                    sup.quote,
                                )
                            elif getattr(sup, "kind", "") in {"aggregate_receipt", "search_comparison"}:
                                await conn.execute(
                                    """
                                    INSERT INTO claim_supports (
                                        answer_id, claim_id, support_index, kind, receipt_id, result_keys
                                    ) VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                                    """,
                                    answer_id,
                                    claim.claim_id,
                                    idx,
                                    sup.kind,
                                    sup.receipt_id,
                                    sup.result_keys,
                                )

                # 3. Mark run completed if not cancelled
                res = await conn.execute(
                    "UPDATE runs SET status = 'completed', completed_at = now() WHERE run_id = $1 AND status != 'cancelled'",
                    run_id,
                )
                if "UPDATE 0" in res:
                    # Run was cancelled; do not advance state revision or overwrite cancellation
                    return -1

                # 4. Advance session state revision and update board
                s_row = await conn.fetchrow(
                    "SELECT state_revision, board FROM sessions WHERE session_id = $1 FOR UPDATE",
                    session_id,
                )
                curr_rev = s_row["state_revision"]
                new_rev = curr_rev + 1

                board_data = [b.model_dump(mode="json") for b in new_board_items]
                await conn.execute(
                    """
                    UPDATE sessions
                    SET state_revision = $2, board = $3::jsonb, updated_at = now()
                    WHERE session_id = $1
                    """,
                    session_id,
                    new_rev,
                    board_data,
                )

                # 5. Insert assistant message into messages table
                seq_row = await conn.fetchrow(
                    "SELECT COALESCE(MAX(sequence), 0) + 1 AS next_seq FROM messages WHERE session_id = $1",
                    session_id,
                )
                next_seq = seq_row["next_seq"]
                await conn.execute(
                    """
                    INSERT INTO messages (message_id, session_id, run_id, sequence, role, source_type, content)
                    VALUES ($1, $2, $3, $4, 'assistant', 'model_answer', $5::jsonb)
                    """,
                    uuid4(),
                    session_id,
                    run_id,
                    next_seq,
                    answer.model_dump(mode="json"),
                )

                return new_rev
