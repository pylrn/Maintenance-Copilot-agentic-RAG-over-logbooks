"""Minimal ID/timing telemetry. No prompts, raw records, credentials or DSNs."""

import json
import logging

logger = logging.getLogger("maintenance")
ALLOWED = {
    "run_id",
    "search_id",
    "stage",
    "elapsed_ms",
    "record_count",
    "status",
    "pipeline_version",
}


def log_stage(**fields):
    logger.info(json.dumps({k: v for k, v in fields.items() if k in ALLOWED}, default=str))
