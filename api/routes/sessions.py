"""Session management and message ingestion routes."""

import asyncio
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from maintenance.auth import require_owner
from maintenance.contracts import MessageRequest
from maintenance.tools import RunDeps

router = APIRouter(tags=["sessions"])


class CreateSessionRequest(BaseModel):
    domain: str = Field(default="aviation", pattern="^(aviation|facility)$")
    title: str = Field(default="New investigation", max_length=120)
    aircraft_profile: dict[str, Any] = Field(default_factory=dict)


class PatchSessionRequest(BaseModel):
    expected_revision: int
    title: str | None = None
    aircraft_profile: dict[str, Any] | None = None


@router.post("/sessions")
async def create_session(
    payload: CreateSessionRequest,
    request: Request,
    owner_id: UUID = Depends(require_owner),
):
    repo = request.app.state.session_repo
    snapshot = await repo.create_session(
        owner_id=owner_id,
        domain=payload.domain,
        title=payload.title,
        aircraft_profile=payload.aircraft_profile,
    )
    return snapshot.model_dump(mode="json")


@router.get("/sessions")
async def list_sessions(
    request: Request,
    owner_id: UUID = Depends(require_owner),
):
    repo = request.app.state.session_repo
    return await repo.list_sessions(owner_id=owner_id)


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: UUID,
    request: Request,
    owner_id: UUID = Depends(require_owner),
):
    repo = request.app.state.session_repo
    snapshot = await repo.get_session(session_id, owner_id)
    if not snapshot:
        raise HTTPException(404, "session_not_found")
    return snapshot.model_dump(mode="json")


@router.patch("/sessions/{session_id}")
async def patch_session(
    session_id: UUID,
    payload: PatchSessionRequest,
    request: Request,
    owner_id: UUID = Depends(require_owner),
):
    repo = request.app.state.session_repo
    try:
        new_rev = await repo.update_session_profile(
            session_id=session_id,
            owner_id=owner_id,
            expected_revision=payload.expected_revision,
            aircraft_profile=payload.aircraft_profile,
            title=payload.title,
        )
        return {"session_id": str(session_id), "state_revision": new_rev}
    except LookupError:
        raise HTTPException(404, "session_not_found")
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: UUID,
    request: Request,
    owner_id: UUID = Depends(require_owner),
):
    repo = request.app.state.session_repo
    deleted = await repo.delete_session(session_id, owner_id)
    if not deleted:
        raise HTTPException(404, "session_not_found")
    return {"session_id": str(session_id), "status": "deleted"}


@router.post("/sessions/{session_id}/messages")
async def post_message(
    session_id: UUID,
    payload: MessageRequest,
    request: Request,
    owner_id: UUID = Depends(require_owner),
):
    """Submits a user message and triggers an evidence-first investigation run."""
    repo = request.app.state.session_repo
    runner = request.app.state.agent_runner

    # Retrieve session domain and corpus IDs
    session_snap = await repo.get_session(session_id, owner_id)
    if not session_snap:
        raise HTTPException(404, "session_not_found")

    engine = request.app.state.search_engine
    corpus_ids = [
        c.manifest.corpus_id
        for c in engine.corpora.values()
        if c.manifest.domain == session_snap.domain
    ] if engine else []

    provider = getattr(request.app.state, "provider", None)
    model_id = provider.model_name if (provider and provider.is_configured) else "extractive/v1"

    try:
        run_id, is_new = await repo.create_run(
            session_id=session_id,
            owner_id=owner_id,
            mode="EVIDENCE",
            idempotency_key=payload.idempotency_key,
            request_text=payload.text,
            expected_revision=payload.expected_revision,
            corpus_ids=corpus_ids,
            model_id=model_id,
        )
    except LookupError:
        raise HTTPException(404, "session_not_found")
    except ValueError as exc:
        err_msg = str(exc)
        if "conflict" in err_msg or "in_progress" in err_msg or "mismatch" in err_msg:
            raise HTTPException(409, err_msg)
        raise HTTPException(400, err_msg)

    if is_new:
        # Build RunDeps and launch runner background task
        deps = RunDeps(
            owner_id=owner_id,
            session_id=session_id,
            run_id=run_id,
            mode="EVIDENCE",
            state_revision=payload.expected_revision,
            corpus_ids=corpus_ids,
            search_engine=request.app.state.search_engine,
            record_service=request.app.state.record_service,
            comparison_service=request.app.state.comparison_service,
            pattern_service=request.app.state.pattern_service,
            visual_service=request.app.state.visual_service,
            fetched_evidence={},
            computed_receipts={},
            tool_events=[],
        )
        asyncio.create_task(runner.execute_run(deps, payload.text, domain=session_snap.domain))

    return {
        "run_id": str(run_id),
        "session_id": str(session_id),
        "mode": "EVIDENCE",
        "state_revision": payload.expected_revision,
        "events_url": f"/api/maintenance/v1/runs/{run_id}/events",
    }
