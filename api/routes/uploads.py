"""File upload and attachment extraction endpoint."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from maintenance.attachments import AttachmentService
from maintenance.auth import require_owner

router = APIRouter(tags=["uploads"])


@router.post("/sessions/{session_id}/attachments")
async def upload_attachment(
    session_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    owner_id: UUID = Depends(require_owner),
):
    repo = request.app.state.session_repo
    session = await repo.get_session(session_id, owner_id)
    if not session:
        raise HTTPException(404, "session_not_found")

    content = await file.read()
    service = AttachmentService(
        max_bytes=request.app.state.settings.max_upload_bytes,
        max_chars=request.app.state.settings.max_extracted_chars,
    )

    try:
        res = await service.process_file(
            filename=file.filename or "uploaded_file",
            content=content,
            mime_type=file.content_type or "application/octet-stream",
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    # Persist in attachments table
    async with request.app.state.pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO attachments (
                attachment_id, owner_id, session_id, content_hash, mime,
                extraction_status, storage_key, trust_type, extracted_text
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            res["attachment_id"],
            owner_id,
            session_id,
            res["content_hash"],
            res["mime"],
            res["extraction_status"],
            res["storage_key"],
            res["trust_type"],
            res["extracted_text"],
        )

    return {
        "attachment_id": str(res["attachment_id"]),
        "filename": res["filename"],
        "content_hash": res["content_hash"],
        "extraction_status": res["extraction_status"],
        "extracted_chars": len(res["extracted_text"]),
        "trust_type": "user_input",
    }
