from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from maintenance.auth import require_owner
from maintenance.contracts import SearchResult, SearchSpec, ServiceScope

router = APIRouter()


@router.post("/search", response_model=SearchResult)
async def search(spec: SearchSpec, request: Request, owner: UUID = Depends(require_owner)):
    engine = request.app.state.search_engine
    if engine is None:
        raise HTTPException(503, "retrieval_unavailable")
    scope = ServiceScope(
        owner_id=owner, corpus_ids=[c.manifest.corpus_id for c in engine.corpora.values()]
    )
    try:
        return await engine.search(spec, scope)
    except (TimeoutError, ConnectionError, RuntimeError, ValueError) as exc:
        raise HTTPException(503, "retrieval_unavailable") from exc
