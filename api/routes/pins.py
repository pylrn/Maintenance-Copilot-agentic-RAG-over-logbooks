"""Evidence record pinning and unpinning routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from maintenance.auth import require_owner

router = APIRouter(tags=["pins"])


class PinRequest(BaseModel):
    user_note: str | None = Field(default=None, max_length=500)
    expected_revision: int = Field(ge=0)


@router.put("/sessions/{session_id}/pins/{domain}/{source_id}")
async def pin_record(
    session_id: UUID,
    domain: str,
    source_id: str,
    payload: PinRequest,
    request: Request,
    owner_id: UUID = Depends(require_owner),
):
    repo = request.app.state.session_repo
    session = await repo.get_session(session_id, owner_id)
    if not session:
        raise HTTPException(404, "session_not_found")

    record_id = f"{domain}:{source_id}"

    async with request.app.state.pool.acquire() as conn:
        # Check that record exists in maintenance_records
        row = await conn.fetchrow(
            """
            SELECT corpus_id FROM maintenance_records
            WHERE record_id = $1
            LIMIT 1
            """,
            record_id,
        )
        if not row:
            raise HTTPException(404, "record_not_found")
        corpus_id = row["corpus_id"]

        await conn.execute(
            """
            INSERT INTO pinned_evidence (session_id, corpus_id, record_id, user_note, pinned_at)
            VALUES ($1, $2, $3, $4, now())
            ON CONFLICT (session_id, corpus_id, record_id)
            DO UPDATE SET user_note = EXCLUDED.user_note, pinned_at = now()
            """,
            session_id,
            corpus_id,
            record_id,
            payload.user_note,
        )

    return {
        "session_id": str(session_id),
        "record_id": record_id,
        "status": "pinned",
    }


@router.delete("/sessions/{session_id}/pins/{domain}/{source_id}")
async def unpin_record(
    session_id: UUID,
    domain: str,
    source_id: str,
    request: Request,
    owner_id: UUID = Depends(require_owner),
):
    repo = request.app.state.session_repo
    session = await repo.get_session(session_id, owner_id)
    if not session:
        raise HTTPException(404, "session_not_found")

    record_id = f"{domain}:{source_id}"

    async with request.app.state.pool.acquire() as conn:
        await conn.execute(
            """
            DELETE FROM pinned_evidence
            WHERE session_id = $1 AND record_id = $2
            """,
            session_id,
            record_id,
        )

    return {
        "session_id": str(session_id),
        "record_id": record_id,
        "status": "unpinned",
    }
