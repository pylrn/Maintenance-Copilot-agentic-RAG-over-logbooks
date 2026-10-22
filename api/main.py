"""Composition root. P2 plugs in api.routes.workflows.router and optional lifecycle hooks."""

import importlib
import importlib.util
import json
import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from api.routes import lab, records, search
from maintenance.auth import IdentitySigner
from maintenance.config import Settings
from maintenance.db import Database
from maintenance.features.compare import ComparisonService
from maintenance.features.patterns import PatternService
from maintenance.features.sensitivity import SensitivityService

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "/api/maintenance/v1"


def create_app(settings=None, search_engine=None):
    settings = settings or Settings()
    workflows = None
    if importlib.util.find_spec("api.routes.workflows") is not None:
        workflows = importlib.import_module("api.routes.workflows")

    @asynccontextmanager
    async def lifespan(app):
        app.state.db = None
        app.state.startup_errors = []
        if settings.database_url:
            try:
                db = Database(
                    settings.database_url.get_secret_value(),
                    settings.db_pool_min,
                    settings.db_pool_max,
                    schema=settings.database_schema,
                    vector_schema=settings.vector_schema,
                    ssl_root_cert=settings.database_ssl_root_cert,
                    statement_cache_size=settings.statement_cache_size,
                )
                await db.open()
                app.state.db = db
                if not await db.ready():
                    app.state.startup_errors.append("schema_not_ready")
                if app.state.search_engine is None and not app.state.startup_errors:
                    import asyncio

                    from maintenance.models.embedding import BGEEncoder
                    from maintenance.retrieval.artifacts import load_bundle
                    from maintenance.retrieval.engine import RetrievalEngine

                    meta = json.loads((settings.artifact_dir / "manifest.json").read_text())
                    ids = list({UUID(e["corpus_id"]) for e in meta["entries"]})
                    corpora = await db.load_corpora(ids)
                    encoder = await asyncio.to_thread(
                        BGEEncoder,
                        settings.embedding_revision,
                        settings.model_cache_dir,
                        settings.embedding_query_prefix,
                    )
                    matrices, _ = await asyncio.to_thread(
                        load_bundle, settings.artifact_dir, corpora, encoder
                    )
                    reranker = None
                    if settings.rerank_enabled:
                        from maintenance.models.reranker import Reranker

                        reranker = await asyncio.to_thread(
                            Reranker, settings.rerank_revision, settings.model_cache_dir
                        )
                    app.state.search_engine = RetrievalEngine(corpora, matrices, encoder, reranker)
                    await asyncio.to_thread(encoder.encode_queries, ["warmup"])
            except Exception as exc:
                # Never include exception text; a driver error may contain connection details.
                app.state.startup_errors.append(type(exc).__name__)
                logging.getLogger("maintenance").error(
                    "platform startup failed: %s", type(exc).__name__
                )
        engine = app.state.search_engine
        app.state.pool = app.state.db.pool if app.state.db else None
        from maintenance.retrieval.records import RecordService

        app.state.record_service = RecordService(app.state.db) if app.state.db else engine
        app.state.pattern_service = PatternService(engine) if engine else None
        app.state.comparison_service = ComparisonService(engine) if engine else None
        app.state.sensitivity_service = SensitivityService(engine) if engine else None
        if workflows and hasattr(workflows, "startup"):
            await workflows.startup(app)
        try:
            yield
        finally:
            if workflows and hasattr(workflows, "shutdown"):
                await workflows.shutdown(app)
            if app.state.db:
                await app.state.db.close()

    app = FastAPI(title="Maintenance Atlas", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.search_engine = search_engine
    app.state.workflows_ready = False
    app.state.workflow_capabilities = {}
    app.state.db = None
    app.state.startup_errors = []
    secret = (
        settings.session_signing_secret.get_secret_value()
        if settings.session_signing_secret
        else secrets.token_hex(40)
    )
    app.state.identity_signer = IdentitySigner(secret, settings.owner_cookie_max_age)
    app.include_router(search.router, prefix=PREFIX)
    app.include_router(records.router, prefix=PREFIX)
    app.include_router(lab.router, prefix=PREFIX + "/lab")
    if workflows:
        app.include_router(workflows.router, prefix=PREFIX)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        code = exc.detail if isinstance(exc.detail, str) else "request_failed"
        return JSONResponse(
            {"error": code, "message": code, "retryable": exc.status_code in {429, 503, 504}},
            status_code=exc.status_code,
        )

    @app.exception_handler(LookupError)
    async def missing(request, exc):
        return JSONResponse(
            {
                "error": "source_not_found",
                "message": "Requested source version is unavailable.",
                "retryable": False,
            },
            status_code=404,
        )

    @app.exception_handler(PermissionError)
    async def forbidden(request, exc):
        return JSONResponse(
            {
                "error": "scope_not_allowed",
                "message": "Source scope is not authorized.",
                "retryable": False,
            },
            status_code=403,
        )

    @app.get(PREFIX + "/health")
    async def health():
        db = app.state.db
        try:
            db_ready = await db.ready() if db else False
        except Exception:
            db_ready = False
        retrieval = app.state.search_engine is not None
        ready = (
            retrieval
            and (db_ready or (settings.app_env == "test" and db is None))
            and not app.state.startup_errors
        )
        return JSONResponse(
            {
                "ready": ready,
                "app_ready": bool(
                    ready
                    and app.state.workflows_ready
                    and app.state.workflow_capabilities.get("agent_ready", False)
                ),
                "retrieval_ready": retrieval,
                "database_ready": db_ready,
                "workflows_ready": app.state.workflows_ready,
                "startup_errors": app.state.startup_errors,
            },
            status_code=200 if ready else 503,
        )

    @app.get(PREFIX + "/capabilities")
    async def capabilities():
        engine = app.state.search_engine
        provider = getattr(app.state, "provider", None)
        if provider is not None:
            is_provider_configured = provider.is_configured
        elif settings.llm_provider == "gemini":
            is_provider_configured = bool(
                settings.gemini_api_key
                and settings.gemini_api_key.get_secret_value()
                and not settings.gemini_api_key.get_secret_value().startswith("REPLACE")
            )
        else:
            is_provider_configured = bool(
                settings.deepseek_api_key
                and settings.deepseek_api_key.get_secret_value()
                and not settings.deepseek_api_key.get_secret_value().startswith("REPLACE")
            )

        return {
            "protocol_version": "maintenance/v1",
            "workflows_ready": app.state.workflows_ready,
            "domains": sorted({c.manifest.domain for c in engine.corpora.values()})
            if engine
            else [],
            "corpora": [c.manifest.model_dump(mode="json") for c in engine.corpora.values()]
            if engine
            else [],
            "configured_models": settings.model_allowlist,
            "provider_configured": is_provider_configured,
            "enabled_modes": list(app.state.workflow_capabilities.get("enabled_modes", []))
            if app.state.workflows_ready
            else [],
            "visuals_available": bool(
                app.state.workflows_ready
                and app.state.workflow_capabilities.get("visuals_available", False)
            ),
            "agent_ready": bool(
                app.state.workflows_ready
                and app.state.workflow_capabilities.get("agent_ready", False)
            ),
            "reranker_available": bool(engine and engine.reranker),
        }

    @app.get("/maintenance")
    @app.get("/maintenance/")
    async def product():
        path = ROOT / "api/static/maintenance/index.html"
        if not path.exists() or not app.state.workflows_ready:
            raise HTTPException(503, "person_two_ui_pending")
        return FileResponse(
            path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    @app.get("/maintenance/{file_path:path}")
    async def maintenance_asset(file_path: str):
        maintenance_root = (ROOT / "api/static/maintenance").resolve()
        asset_path = (maintenance_root / file_path).resolve()
        if not str(asset_path).startswith(str(maintenance_root)):
            raise HTTPException(403, "forbidden")
        if asset_path.is_file():
            return FileResponse(asset_path)
        index_path = maintenance_root / "index.html"
        if index_path.is_file():
            return FileResponse(index_path)
        raise HTTPException(404, "not_found")

    @app.get("/retrieval-lab")
    async def retrieval_lab():
        path = ROOT / "api/static/retrieval_lab.html"
        if not path.exists():
            raise HTTPException(404, "retrieval_lab_not_found")
        return FileResponse(
            path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    static = ROOT / "api/static"
    if static.is_dir():
        app.mount("/static", StaticFiles(directory=static), name="static")
    return app


app = create_app()
