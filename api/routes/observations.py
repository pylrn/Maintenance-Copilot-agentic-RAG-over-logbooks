"""Explicit user observation and field measurement routes."""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from maintenance.auth import require_owner
from maintenance.board import BoardManager

router = APIRouter(tags=["observations"])


class ObservationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    expected_revision: int = Field(ge=0)
    affected_components: list[str] = Field(default_factory=list)


@router.post("/sessions/{session_id}/observations")
async def add_observation(
    session_id: UUID,
    payload: ObservationRequest,
    request: Request,
    owner_id: UUID = Depends(require_owner),
):
    repo = request.app.state.session_repo
    session = await repo.get_session(session_id, owner_id)
    if not session:
        raise HTTPException(404, "session_not_found")
    if session.state_revision != payload.expected_revision:
        raise HTTPException(
            409,
            f"state_revision_conflict: expected {payload.expected_revision} got {session.state_revision}",
        )

    new_board = BoardManager.add_user_observation(
        board=session.board,
        text=payload.text,
        state_revision=payload.expected_revision,
        affected_components=payload.affected_components,
    )

    new_rev = payload.expected_revision + 1
    board_json = json.dumps([b.model_dump(mode="json") for b in new_board])

    async with request.app.state.pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE sessions
            SET state_revision = $2, board = $3::jsonb, updated_at = now()
            WHERE session_id = $1 AND owner_id = $4
            """,
            session_id,
            new_rev,
            board_json,
            owner_id,
        )

    return {
        "session_id": str(session_id),
        "state_revision": new_rev,
        "board_items_count": len(new_board),
    }
