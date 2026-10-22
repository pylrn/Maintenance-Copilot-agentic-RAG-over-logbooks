"""Run event streaming and cancellation routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from maintenance.auth import require_owner

router = APIRouter(tags=["runs"])


@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: UUID,
    request: Request,
    after: int = Query(default=0, ge=0),
    owner_id: UUID = Depends(require_owner),
):
    repo = request.app.state.session_repo
    actual_owner = await repo.get_run_owner(run_id)
    if not actual_owner or actual_owner != owner_id:
        raise HTTPException(404, "run_not_found")

    event_bus = request.app.state.event_bus

    return StreamingResponse(
        event_bus.subscribe(run_id, after_sequence=after),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/runs/{run_id}/cancel")
async def cancel_run(
    run_id: UUID,
    request: Request,
    owner_id: UUID = Depends(require_owner),
):
    repo = request.app.state.session_repo
    event_bus = request.app.state.event_bus

    cancelled = await repo.cancel_run(run_id, owner_id)
    if cancelled:
        # Cancel background task if tracked
        active_tasks = getattr(request.app.state, "active_tasks", {})
        task = active_tasks.get(run_id)
        if task and not task.done():
            task.cancel()

        next_seq = await event_bus.get_next_sequence(run_id)
        await event_bus.emit(
            run_id,
            sequence=next_seq,
            event_type="run_cancelled",
            data={"run_id": str(run_id), "cancelled": True},
        )
        return {"run_id": str(run_id), "status": "cancelled"}
    raise HTTPException(404, "run_not_found_or_not_cancellable")
