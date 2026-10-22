"""Unit tests for agent tools, runner loop, and refusal handling."""

from uuid import uuid4

import pytest

from maintenance.answer_rendering import render_extractive_answer
from maintenance.features.visuals import VisualService


@pytest.mark.asyncio
async def test_extractive_answer_renders_supported_historical_claims():
    run_id = uuid4()
    ev_id_prob = uuid4()
    ev_id_act = uuid4()

    fetched = {
        ev_id_prob: {
            "evidence_id": ev_id_prob,
            "corpus_id": uuid4(),
            "record_id": "aviation:100009",
            "field": "PROBLEM",
            "raw_text": "#2 INTAKE IS LEAKING.",
            "source_sha256": "abc123hash",
        },
        ev_id_act: {
            "evidence_id": ev_id_act,
            "corpus_id": uuid4(),
            "record_id": "aviation:100009",
            "field": "ACTION",
            "raw_text": "REMOVED & REPLACED #2 INTAKE GASKET.",
            "source_sha256": "def456hash",
        },
    }

    ans = render_extractive_answer(
        run_id=run_id,
        mode="EVIDENCE",
        query_raw="CYL #2 intake leaking",
        fetched_evidence=fetched,
        state_revision=1,
    )

    assert ans.status == "supported_historical"
    assert len(ans.claims) == 2
    assert ans.claims[0].claim_type == "historical_problem"
    assert ans.claims[1].claim_type == "historical_action"
    assert len(ans.allowed_actions) >= 4  # hypothesis, challenge, sensitivity, handover


def test_visual_service_loads_component_context_and_mappings():
    vis = VisualService()
    ctx = vis.get_component_context("intake_gasket")
    assert ctx.component_id == "intake_gasket"
    assert "Intake" in ctx.name
    assert "node-intake-gasket" in ctx.asset_mapping_ids
    assert len(ctx.citations) > 0
    assert ctx.applicability == "generic"


def test_unsupported_torque_request_renders_insufficient_evidence():
    run_id = uuid4()
    ans = render_extractive_answer(
        run_id=run_id,
        mode="EVIDENCE",
        query_raw="What is the torque spec in ft-lbs for intake flange?",
        fetched_evidence={},
        state_revision=0,
        status="insufficient_evidence",
        limitations=["Torque specifications absent from historical maintenance logs."],
    )
    assert ans.status == "insufficient_evidence"
    assert len(ans.claims) == 0
    assert "Torque specifications absent" in ans.limitations[0]
