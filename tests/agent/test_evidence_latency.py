"""Evidence prefetch must not trigger redundant model tool loops."""
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from maintenance.agent_run import AgentRunner


@pytest.mark.asyncio
@pytest.mark.parametrize("model_failure", [False, True])
@pytest.mark.parametrize("query, supported", [("right brake loose", True), ("right brake leak", False), ("CYL #99 intake leak", False), ("quantum stabilizer resonance", False), ("Is the aircraft safe to fly after this intake leak?", False)])
async def test_evidence_uses_one_synthesis_and_keeps_validated_fallback(monkeypatch, model_failure, query, supported):
    raw = "RIGHT BRAKE IS LOOSE."
    eid = uuid4()
    evidence = {eid: {
        "evidence_id": eid, "corpus_id": uuid4(), "record_id": "aviation:1",
        "field": "PROBLEM", "raw_text": raw,
        "source_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "text_sha256": hashlib.sha256(raw.encode()).hexdigest(),
    }}
    deps = SimpleNamespace(
        run_id=uuid4(), session_id=uuid4(), owner_id=uuid4(), mode="EVIDENCE",
        state_revision=0, corpus_ids=[], fetched_evidence=evidence,
        computed_receipts={}, record_service=None, model_id="test-model", tool_events=[],
    )
    search = AsyncMock(return_value={"hits": [{"record_id": "aviation:1", "compatibility": "direct"}]})
    monkeypatch.setattr("maintenance.agent_run.tool_search_records", search)
    monkeypatch.setattr("maintenance.agent_run.tool_get_records", AsyncMock(return_value={"records": []}))
    provider = SimpleNamespace(is_configured=True, model_name="test-model", provider_type="gemini",
        roundtrip_tool_loop=AsyncMock(), chat_completion=AsyncMock(
            return_value={"content": json.dumps({"decision":"supported_historical","records":[{"problem_evidence_id":str(eid),"action_evidence_ids":[]}]})}))
    if model_failure:
        provider.chat_completion.side_effect = TimeoutError("test timeout")
    repo = SimpleNamespace(get_session=AsyncMock(return_value=None),
        save_evidence_snapshots=AsyncMock(), commit_answer_and_state=AsyncMock(return_value=1))
    answer = await AgentRunner(repo, SimpleNamespace(emit=AsyncMock()), provider).execute_run(deps, query)
    search.assert_awaited_once()
    provider.roundtrip_tool_loop.assert_not_awaited()
    if supported:
        provider.chat_completion.assert_awaited_once()
        assert answer.generation["status"] == ("extractive_fallback" if model_failure else "validated_selection")
        assert answer.status == "supported_historical"
        assert answer.claims[0].supports[0].evidence_id == eid
    else:
        provider.chat_completion.assert_not_awaited()
        assert answer.status == "insufficient_evidence"
        assert answer.claims == []
        assert answer.visual_refs == []
        assert answer.allowed_actions == []
        assert "Insufficient evidence" in answer.summary
    assert repo.commit_answer_and_state.call_args.kwargs["validation_report"]["valid"]
