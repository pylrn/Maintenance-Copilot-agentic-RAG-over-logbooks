"""Master workflow router aggregator and lifecycle hooks."""

import logging

from fastapi import APIRouter

from api.routes import (
    actions,
    feedback,
    observations,
    pins,
    runs,
    sessions,
    uploads,
    visuals,
)
from maintenance.agent_run import AgentRunner
from maintenance.events import EventBus
from maintenance.features.challenge import ChallengeService
from maintenance.features.visuals import VisualService
from maintenance.models.provider import LLMProvider
from maintenance.session_repository import SessionRepository

logger = logging.getLogger("maintenance.workflows")

router = APIRouter()

# Mount all Person 2 subrouters
router.include_router(sessions.router)
router.include_router(runs.router)
router.include_router(actions.router)
router.include_router(uploads.router)
router.include_router(visuals.router)
router.include_router(observations.router)
router.include_router(feedback.router)
router.include_router(pins.router)


async def startup(app):
    """Initializes workflow repositories, event bus, agent runner, and services."""
    pool = app.state.pool
    settings = app.state.settings

    app.state.visual_service = VisualService()

    if not pool:
        logger.info("Database pool not available; workflow engine deferred.")
        return

    app.state.session_repo = SessionRepository(pool)
    app.state.event_bus = EventBus(pool)
    app.state.challenge_service = ChallengeService(
        app.state.search_engine, app.state.record_service
    )

    if settings.llm_provider == "gemini" or (
        settings.llm_provider == "auto"
        and settings.gemini_api_key
        and not settings.deepseek_api_key
    ):
        app.state.provider = LLMProvider(
            api_key=settings.gemini_api_key,
            base_url=settings.gemini_base_url,
            model_name=settings.gemini_model,
            provider_type="gemini",
        )
    else:
        app.state.provider = LLMProvider(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model_name=settings.deepseek_model,
            provider_type="deepseek",
        )

    app.state.agent_runner = AgentRunner(
        repository=app.state.session_repo,
        event_bus=app.state.event_bus,
        provider=app.state.provider,
    )

    app.state.workflow_capabilities = {
        "enabled_modes": [
            "EVIDENCE",
            "HYPOTHESIS",
            "CHALLENGE",
            "DISTINGUISH",
            "SENSITIVITY",
            "HANDOVER",
        ],
        "visuals_available": True,
        "agent_ready": True,
    }
    app.state.workflows_ready = True
    logger.info("Maintenance Atlas workflow engine and routes initialized successfully.")


async def shutdown(app):
    """Graceful shutdown for workflow background tasks."""
    app.state.workflows_ready = False
    logger.info("Maintenance Atlas workflow engine shut down.")
