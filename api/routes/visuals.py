"""Reviewed 2D visual schematics and educational component context routes."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from maintenance.features.visuals import VisualService

router = APIRouter(tags=["visuals"])


@router.get("/visuals/{asset_id}")
async def get_visual_asset(asset_id: str, request: Request):
    visual_service = getattr(request.app.state, "visual_service", None) or VisualService()
    info = visual_service.get_asset_info(asset_id)
    if not info or not info.get("exists"):
        raise HTTPException(404, "visual_asset_not_found")

    file_path = Path(info["file_path"])
    return FileResponse(file_path, media_type="image/svg+xml")


@router.get("/components/{component_id}/context")
async def get_component_context(component_id: str, request: Request):
    visual_service = getattr(request.app.state, "visual_service", None) or VisualService()
    envelope = visual_service.get_component_context(component_id)
    return envelope.model_dump(mode="json")
