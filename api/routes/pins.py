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
    repo = getattr(request.app.state, "session_repo", None)
    pool = getattr(request.app.state, "pool", None)
    if not repo or not pool:
        raise HTTPException(503, "workflows_unavailable")
    session = await repo.get_session(session_id, owner_id)
    if not session:
        raise HTTPException(404, "session_not_found")

    record_id = f"{domain}:{source_id}"

    async with pool.acquire() as conn:
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
    repo = getattr(request.app.state, "session_repo", None)
    pool = getattr(request.app.state, "pool", None)
    if not repo or not pool:
        raise HTTPException(503, "workflows_unavailable")
    session = await repo.get_session(session_id, owner_id)
    if not session:
        raise HTTPException(404, "session_not_found")

    record_id = f"{domain}:{source_id}"

    async with pool.acquire() as conn:
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


@router.get("/sessions/{session_id}/pins")
async def list_pins(
    session_id: UUID,
    request: Request,
    owner_id: UUID = Depends(require_owner),
):
    repo = getattr(request.app.state, "session_repo", None)
    pool = getattr(request.app.state, "pool", None)
    if not repo or not pool:
        raise HTTPException(503, "workflows_unavailable")

    session = await repo.get_session(session_id, owner_id)
    if not session:
        raise HTTPException(404, "session_not_found")

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT corpus_id, record_id, user_note, pinned_at
            FROM pinned_evidence
            WHERE session_id = $1
            ORDER BY pinned_at DESC
            """,
            session_id,
        )
        return [
            {
                "session_id": str(session_id),
                "corpus_id": str(r["corpus_id"]),
                "record_id": r["record_id"],
                "domain": r["record_id"].split(":", 1)[0] if ":" in r["record_id"] else "aviation",
                "source_id": r["record_id"].split(":", 1)[1] if ":" in r["record_id"] else r["record_id"],
                "user_note": r["user_note"],
                "pinned_at": r["pinned_at"].isoformat() if r["pinned_at"] else None,
            }
            for r in rows
        ]
