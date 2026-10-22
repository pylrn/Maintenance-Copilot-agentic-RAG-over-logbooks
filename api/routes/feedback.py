"""User feedback recording route."""

import json
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from maintenance.auth import require_owner

router = APIRouter(tags=["feedback"])


class FeedbackRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=200)
    source_ids: list[str] = Field(default_factory=list)
    user_note: str | None = Field(default=None, max_length=2000)


@router.post("/answers/{answer_id}/feedback")
async def record_feedback(
    answer_id: UUID,
    payload: FeedbackRequest,
    request: Request,
    owner_id: UUID = Depends(require_owner),
):
    feedback_id = uuid4()
    async with request.app.state.pool.acquire() as conn:
        ans = await conn.fetchrow("SELECT answer_id FROM answers WHERE answer_id = $1", answer_id)
        if not ans:
            raise HTTPException(404, "answer_not_found")

        await conn.execute(
            """
            INSERT INTO feedback (feedback_id, answer_id, owner_id, reason, source_ids, user_note, review_status)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, 'pending')
            """,
            feedback_id,
            answer_id,
            owner_id,
            payload.reason,
            json.dumps(payload.source_ids),
            payload.user_note,
        )

    return {
        "feedback_id": str(feedback_id),
        "status": "recorded",
    }
