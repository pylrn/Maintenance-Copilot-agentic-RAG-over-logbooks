from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from maintenance.auth import require_owner
from maintenance.contracts import Domain, RecordSnapshot, ServiceScope

router = APIRouter()


@router.get("/records/{domain}/{source_id}", response_model=RecordSnapshot)
async def get_record(
    domain: Domain,
    source_id: str,
    request: Request,
    corpus_id: UUID | None = Query(default=None),
    corpus_version: UUID | None = Query(default=None),
    owner: UUID = Depends(require_owner),
):
    cid = corpus_id or corpus_version
    if cid is None:
        raise HTTPException(422, "corpus_id_or_version_required")

    engine = request.app.state.search_engine
    if engine is None:
        raise HTTPException(503, "retrieval_unavailable")
    if str(cid) not in engine.corpora and not request.app.state.db:
        raise HTTPException(404, "source_not_found")
    return (
        await request.app.state.record_service.fetch(
            [f"{domain}:{source_id}"], ServiceScope(owner_id=owner, corpus_ids=[cid])
        )
    )[0]
