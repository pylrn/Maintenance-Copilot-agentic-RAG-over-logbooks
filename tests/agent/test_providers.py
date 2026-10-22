"""Unit and mocked tests for DeepSeek and Gemini provider adapters, tool roundtrips, and redaction."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import SecretStr, ValidationError

from maintenance.answer_validation import validate_claim
from maintenance.config import Settings
from maintenance.contracts import Claim, SupportSpan
from maintenance.db import Database
from maintenance.models.provider import LLMProvider


def test_provider_settings_allowlist_and_endpoints():
    s = Settings(
        app_env="test",
        gemini_api_key=SecretStr("test-gemini-key"),
        deepseek_api_key=SecretStr("test-deepseek-key"),
    )
    assert s.deepseek_base_url == "https://api.deepseek.com"
    assert s.gemini_base_url == "https://generativelanguage.googleapis.com/v1beta/openai/"
    assert "deepseek-flash" in s.model_allowlist
    assert "gemini-3.8-flash" in s.model_allowlist
    assert "gemini-2.5-flash" in s.model_allowlist


def test_production_fails_if_selected_provider_key_missing():
    # Valid production settings except missing deepseek_api_key
    with pytest.raises(ValidationError, match="deepseek_api_key must be configured for deepseek provider"):
        Settings(
            app_env="production",
            app_origin="https://copilot.example.com",
            embedding_revision="5c38ec7c405ec4b44b94cc5a9bb96e735b38267a",
            database_url=SecretStr("postgresql://user:pass@localhost:5432/db"),
            session_signing_secret=SecretStr("x" * 40),
            llm_provider="deepseek",
            gemini_api_key=SecretStr("gemini-secret-key-12345"),
            deepseek_api_key=None,
            _env_file=None,
        )

    # Valid production settings except missing gemini_api_key
    with pytest.raises(ValidationError, match="gemini_api_key must be configured for gemini provider"):
        Settings(
            app_env="production",
            app_origin="https://copilot.example.com",
            embedding_revision="5c38ec7c405ec4b44b94cc5a9bb96e735b38267a",
            database_url=SecretStr("postgresql://user:pass@localhost:5432/db"),
            session_signing_secret=SecretStr("x" * 40),
            llm_provider="gemini",
            deepseek_api_key=SecretStr("deepseek-secret-key-12345"),
            gemini_api_key=None,
            _env_file=None,
        )


def test_db_rejects_invalid_schema_identifiers():
    with pytest.raises(ValueError, match="invalid schema identifier"):
        Database("postgresql://localhost:5432/db", schema="public; DROP TABLE students")

    with pytest.raises(ValueError, match="invalid vector schema identifier"):
        Database("postgresql://localhost:5432/db", vector_schema="ext; SELECT 1")


@pytest.mark.asyncio
async def test_db_fails_when_configured_ca_missing():
    db = Database(
        "postgresql://localhost:5432/db",
        ssl_root_cert="/nonexistent/path/to/missing-ca.crt",
    )
    with pytest.raises(FileNotFoundError, match="Configured CA certificate not found"):
        await db.open()


def test_provider_redacts_credentials_in_repr():
    secret_key = "AIzaSySecretGoogleApiKey1234567890"
    p = LLMProvider(
        api_key=SecretStr(secret_key),
        provider_type="gemini",
        model_name="gemini-2.5-flash",
    )
    rep = repr(p)
    assert secret_key not in rep
    assert "configured" in rep
    assert p.provider_type == "gemini"


def test_provider_rejects_disallowed_base_url():
    with pytest.raises(ValueError, match="disallowed provider base_url"):
        LLMProvider(
            api_key=SecretStr("key"),
            base_url="https://evil-proxy.com/v1",
            provider_type="deepseek",
        )


def test_provider_rejects_disallowed_model():
    with pytest.raises(ValueError, match="not in gemini allowlist"):
        LLMProvider(
            api_key=SecretStr("key"),
            provider_type="gemini",
            model_name="unapproved-model-v99",
        )


@pytest.mark.asyncio
async def test_deepseek_sends_non_thinking_extra_body():
    provider = LLMProvider(
        api_key=SecretStr("test-key"),
        provider_type="deepseek",
        model_name="deepseek-flash",
    )

    mock_resp = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.role = "assistant"
    mock_choice.message.content = "Diagnosis: intake leak."
    mock_choice.message.tool_calls = None
    mock_resp.choices = [mock_choice]
    mock_resp.usage.prompt_tokens = 10
    mock_resp.usage.completion_tokens = 5

    with patch.object(
        provider.client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_resp

        messages = [{"role": "user", "content": "Help with cylinder 2"}]
        resp = await provider.chat_completion(messages=messages)

        assert resp["content"] == "Diagnosis: intake leak."
        mock_create.assert_called_once()
        _, kwargs = mock_create.call_args
        assert kwargs["model"] == "deepseek-flash"
        assert kwargs["extra_body"] == {"thinking": {"type": "disabled"}}


@pytest.mark.asyncio
async def test_gemini_standard_openai_format_without_thinking_flag():
    provider = LLMProvider(
        api_key=SecretStr("test-gemini-key"),
        provider_type="gemini",
        model_name="gemini-2.5-flash",
    )

    mock_resp = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.role = "assistant"
    mock_choice.message.content = "Grounded maintenance check."
    mock_choice.message.tool_calls = None
    mock_resp.choices = [mock_choice]
    mock_resp.usage.prompt_tokens = 15
    mock_resp.usage.completion_tokens = 8

    with patch.object(
        provider.client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_resp

        messages = [{"role": "user", "content": "Query"}]
        resp = await provider.chat_completion(messages=messages)

        assert resp["content"] == "Grounded maintenance check."
        mock_create.assert_called_once()
        _, kwargs = mock_create.call_args
        assert kwargs["model"] == "gemini-2.5-flash"
        assert "extra_body" not in kwargs


@pytest.mark.asyncio
async def test_bounded_tool_call_roundtrip_retains_tool_call_ids():
    provider = LLMProvider(
        api_key=SecretStr("test-key"),
        provider_type="gemini",
        model_name="gemini-2.5-flash",
    )

    tool_call_mock = MagicMock()
    tool_call_mock.id = "call_abc123_unique"
    tool_call_mock.function.name = "search_records"
    tool_call_mock.function.arguments = json.dumps({"query": "intake leak"})

    resp1 = MagicMock()
    choice1 = MagicMock()
    choice1.message.role = "assistant"
    choice1.message.content = ""
    choice1.message.tool_calls = [tool_call_mock]
    resp1.choices = [choice1]
    resp1.usage.prompt_tokens = 20
    resp1.usage.completion_tokens = 10

    resp2 = MagicMock()
    choice2 = MagicMock()
    choice2.message.role = "assistant"
    choice2.message.content = "Grounded finding: 100009"
    choice2.message.tool_calls = None
    resp2.choices = [choice2]
    resp2.usage.prompt_tokens = 35
    resp2.usage.completion_tokens = 12

    with patch.object(
        provider.client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.side_effect = [resp1, resp2]

        initial_messages = [{"role": "user", "content": "Search intake"}]
        tools = [{"type": "function", "function": {"name": "search_records"}}]

        async def fake_search(args):
            assert args["query"] == "intake leak"
            return {"hits": [{"record_id": "aviation:100009"}]}

        final_resp, message_history = await provider.roundtrip_tool_loop(
            messages=initial_messages,
            tools=tools,
            tool_dispatch={"search_records": fake_search},
            max_turns=3,
        )

        assert final_resp["content"] == "Grounded finding: 100009"
        assert mock_create.call_count == 2

        tool_messages = [m for m in message_history if m.get("role") == "tool"]
        assert len(tool_messages) == 1
        assert tool_messages[0]["tool_call_id"] == "call_abc123_unique"
        assert "aviation:100009" in tool_messages[0]["content"]


# =========================================================================
# Adversarial Claim & Citation Validation Tests
# =========================================================================

def _sample_evidence(corpus_id=None):
    cid = corpus_id or uuid4()
    ev_id = uuid4()
    import hashlib
    raw = "#2 INTAKE IS LEAKING."
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return ev_id, {
        ev_id: {
            "evidence_id": ev_id,
            "corpus_id": cid,
            "record_id": "aviation:100009",
            "field": "PROBLEM",
            "raw_text": raw,
            "source_sha256": digest,
        }
    }


def test_claim_with_valid_quote_plus_unsupported_suffix_fails():
    cid = uuid4()
    ev_id, fetched = _sample_evidence(cid)
    raw = fetched[ev_id]["raw_text"]
    digest = fetched[ev_id]["source_sha256"]

    sup = SupportSpan(
        evidence_id=ev_id,
        corpus_id=cid,
        record_id="aviation:100009",
        field="PROBLEM",
        start=0,
        end=len(raw),
        quote=raw,
        source_sha256=digest,
    )

    # Valid quote but arbitrary adversarial conclusion attached
    claim = Claim(
        claim_id="adversarial-claim-1",
        text=f"{raw} therefore replace the engine tomorrow",
        claim_type="historical_problem",
        supports=[sup],
    )
    errors = validate_claim(claim, fetched, {}, mode="EVIDENCE")
    assert any("unsupported_claim_content" in e for e in errors)


def test_claim_with_negated_words_fails():
    cid = uuid4()
    ev_id, fetched = _sample_evidence(cid)
    raw = fetched[ev_id]["raw_text"]
    digest = fetched[ev_id]["source_sha256"]

    sup = SupportSpan(
        evidence_id=ev_id,
        corpus_id=cid,
        record_id="aviation:100009",
        field="PROBLEM",
        start=0,
        end=len(raw),
        quote=raw,
        source_sha256=digest,
    )

    claim = Claim(
        claim_id="adversarial-claim-2",
        text="#2 INTAKE IS NOT LEAKING.",
        claim_type="historical_problem",
        supports=[sup],
    )
    errors = validate_claim(claim, fetched, {}, mode="EVIDENCE")
    assert any("unsupported_claim_content" in e for e in errors)


def test_claim_with_corpus_id_mismatch_fails():
    authoritative_cid = uuid4()
    tampered_cid = uuid4()
    ev_id, fetched = _sample_evidence(authoritative_cid)
    raw = fetched[ev_id]["raw_text"]
    digest = fetched[ev_id]["source_sha256"]

    sup = SupportSpan(
        evidence_id=ev_id,
        corpus_id=tampered_cid,  # Wrong corpus!
        record_id="aviation:100009",
        field="PROBLEM",
        start=0,
        end=len(raw),
        quote=raw,
        source_sha256=digest,
    )

    claim = Claim(
        claim_id="claim-corpus-mismatch",
        text=f'Record aviation:100009 records problem: "{raw}"',
        claim_type="historical_problem",
        supports=[sup],
    )
    errors = validate_claim(claim, fetched, {}, mode="EVIDENCE")
    assert any("citation_identity_mismatch" in e for e in errors)


def test_claim_field_type_mismatch_fails():
    cid = uuid4()
    ev_id, fetched = _sample_evidence(cid)
    raw = fetched[ev_id]["raw_text"]
    digest = fetched[ev_id]["source_sha256"]

    sup = SupportSpan(
        evidence_id=ev_id,
        corpus_id=cid,
        record_id="aviation:100009",
        field="PROBLEM",  # PROBLEM field
        start=0,
        end=len(raw),
        quote=raw,
        source_sha256=digest,
    )

    # Claim asserts historical_action over a PROBLEM field
    claim = Claim(
        claim_id="claim-field-mismatch",
        text=f'Record aviation:100009 records action: "{raw}"',
        claim_type="historical_action",
        supports=[sup],
    )
    errors = validate_claim(claim, fetched, {}, mode="EVIDENCE")
    assert any("claim_type_field_mismatch" in e for e in errors)


def test_claim_matching_approved_template_succeeds():
    cid = uuid4()
    ev_id, fetched = _sample_evidence(cid)
    raw = fetched[ev_id]["raw_text"]
    digest = fetched[ev_id]["source_sha256"]

    sup = SupportSpan(
        evidence_id=ev_id,
        corpus_id=cid,
        record_id="aviation:100009",
        field="PROBLEM",
        start=0,
        end=len(raw),
        quote=raw,
        source_sha256=digest,
    )

    claim = Claim(
        claim_id="claim-valid-template",
        text=f'Record aviation:100009 records problem: "{raw}"',
        claim_type="historical_problem",
        supports=[sup],
    )
    errors = validate_claim(claim, fetched, {}, mode="EVIDENCE")
    assert errors == []


@pytest.mark.asyncio
async def test_roundtrip_hanging_handler_terminates_within_deadline():
    import time

    provider = LLMProvider(
        api_key=SecretStr("test-key"),
        provider_type="gemini",
        model_name="gemini-2.5-flash",
    )

    tool_call_mock = MagicMock()
    tool_call_mock.id = "call_hanging_123"
    tool_call_mock.function.name = "slow_search"
    tool_call_mock.function.arguments = json.dumps({"query": "hang"})

    resp1 = MagicMock()
    choice1 = MagicMock()
    choice1.message.role = "assistant"
    choice1.message.content = ""
    choice1.message.tool_calls = [tool_call_mock]
    resp1.choices = [choice1]
    resp1.usage.prompt_tokens = 10
    resp1.usage.completion_tokens = 5

    with patch.object(
        provider.client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = resp1

        async def hanging_tool(args):
            await asyncio.sleep(5.0)
            return {"status": "never_reached"}

        t0 = time.perf_counter()
        final_resp, message_history = await provider.roundtrip_tool_loop(
            messages=[{"role": "user", "content": "hang"}],
            tools=[{"type": "function", "function": {"name": "slow_search"}}],
            tool_dispatch={"slow_search": hanging_tool},
            max_turns=3,
            deadline_seconds=0.15,
        )
        elapsed = time.perf_counter() - t0

        # Must terminate promptly within ~0.35s despite 5.0s hanging sleep
        assert elapsed < 0.45


@pytest.mark.asyncio
async def test_roundtrip_tool_budget_exhaustion_terminates_without_extra_model_call():
    provider = LLMProvider(
        api_key=SecretStr("test-key"),
        provider_type="gemini",
        model_name="gemini-2.5-flash",
    )

    tc1 = MagicMock()
    tc1.id = "call_1"
    tc1.function.name = "tool_1"
    tc1.function.arguments = "{}"

    tc2 = MagicMock()
    tc2.id = "call_2"
    tc2.function.name = "tool_2"
    tc2.function.arguments = "{}"

    resp1 = MagicMock()
    choice1 = MagicMock()
    choice1.message.role = "assistant"
    choice1.message.content = ""
    choice1.message.tool_calls = [tc1, tc2]
    resp1.choices = [choice1]
    resp1.usage.prompt_tokens = 10
    resp1.usage.completion_tokens = 5

    with patch.object(
        provider.client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = resp1

        called = []

        def t1(args):
            called.append("tool_1")
            return {"ok": 1}

        def t2(args):
            called.append("tool_2")
            return {"ok": 2}

        # max_tool_calls is 1, so tool_1 executes, tool_2 is answered with budget exhausted
        final_resp, history = await provider.roundtrip_tool_loop(
            messages=[{"role": "user", "content": "run"}],
            tools=[],
            tool_dispatch={"tool_1": t1, "tool_2": t2},
            max_turns=3,
            max_tool_calls=1,
            deadline_seconds=5.0,
        )

        # Crucial check: model was called ONLY ONCE, no extra roundtrip!
        assert mock_create.call_count == 1
        assert called == ["tool_1"]

        # Ensure all emitted tool calls were answered so message history is structurally valid
        tool_messages = [m for m in history if m.get("role") == "tool"]
        assert len(tool_messages) == 2
        assert tool_messages[0]["tool_call_id"] == "call_1"
        assert tool_messages[1]["tool_call_id"] == "call_2"
        assert "tool_budget_exhausted" in tool_messages[1]["content"]


@pytest.mark.asyncio
async def test_save_model_messages_persists_jsonb_array_and_exact_ids():
    import os
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("isolated PostgreSQL required")

    from maintenance.session_repository import SessionRepository

    db = Database(os.environ["TEST_DATABASE_URL"])
    await db.open()
    try:
        repo = SessionRepository(db.pool)
        owner = uuid4()
        session = await repo.create_session(owner, "aviation", "Transcript Test")
        run_id = uuid4()

        # Insert a run
        await db.pool.execute(
            """
            INSERT INTO runs (run_id, session_id, mode, idempotency_key, request_hash, state_revision, corpus_ids, prompt_version, model_id, status)
            VALUES ($1, $2, 'EVIDENCE', $3, $4, 0, '[]', 'v1', 'gemini-2.5-flash', 'running')
            """,
            run_id,
            session.session_id,
            uuid4(),
            "h" * 64,
        )

        transcript = [
            {"role": "user", "content": "Help with cylinder 2"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_exact_id_9988",
                        "type": "function",
                        "function": {"name": "search_records", "arguments": '{"query": "cylinder"}'},
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_exact_id_9988",
                "name": "search_records",
                "content": '{"status": "ok"}',
            },
        ]

        await repo.save_model_messages(
            run_id=run_id,
            turn_index=0,
            messages=transcript,
            provider="gemini",
        )

        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT jsonb_typeof(serialized_messages) AS typeof, serialized_messages, provider FROM model_messages WHERE run_id=$1",
                run_id,
            )
            assert row is not None
            assert row["typeof"] == "array"
            assert row["provider"] == "gemini"
            saved_messages = row["serialized_messages"]
            assert len(saved_messages) == 3
            assert saved_messages[1]["tool_calls"][0]["id"] == "call_exact_id_9988"
            assert saved_messages[2]["tool_call_id"] == "call_exact_id_9988"
    finally:
        await db.close()


def test_malformed_dsn_redaction_does_not_leak_key_value_secrets():
    from scripts.db_preflight import extract_target_info

    malformed = "dbname=test user=someone password=FAKE_SECRET"
    info = extract_target_info(malformed)
    assert "FAKE_SECRET" not in info["database"]
    assert "FAKE_SECRET" not in info["redacted_dsn"]
    assert "FAKE_SECRET" not in info["host"]
    assert info["database"] == "redacted"
    assert info["redacted_dsn"] == "postgresql://***:***@<redacted>"


@pytest.mark.asyncio
async def test_facility_get_records_preserves_description_and_passes_validation_gate():
    import hashlib

    from maintenance.answer_rendering import render_extractive_answer
    from maintenance.answer_validation import validate_answer
    from maintenance.contracts import RecordSnapshot
    from maintenance.tools import RunDeps, tool_get_records

    cid = uuid4()
    desc_text = "WATER LEAK IN BOILER ROOM CORRIDOR."
    desc_sha = hashlib.sha256(desc_text.encode("utf-8")).hexdigest()

    rec = RecordSnapshot(
        corpus_id=cid,
        record_id="facility:9901",
        source_id="9901",
        domain="facility",
        csv_row=10,
        original_fields={"WORK_ID": "9901", "DESCRIPTION": desc_text},
        problem_raw=desc_text,
        action_raw=None,
        problem_normalized=desc_text.lower(),
        action_normalized=None,
        duplicate_key="dupkey",
        source_file_sha256="filesha" * 8,
        field_sha256={"DESCRIPTION": desc_sha},
    )

    class MockRecordService:
        async def fetch(self, record_ids, scope):
            return [rec]

    deps = RunDeps(
        owner_id=uuid4(),
        session_id=uuid4(),
        run_id=uuid4(),
        mode="EVIDENCE",
        state_revision=0,
        corpus_ids=[cid],
        search_engine=None,
        record_service=MockRecordService(),
        comparison_service=None,
        pattern_service=None,
        visual_service=None,
        fetched_evidence={},
        computed_receipts={},
        tool_events=[],
    )

    res = await tool_get_records(deps, ["facility:9901"])
    record_entry = res["records"][0]
    # No fabricated ACTION or evidence ID for facility
    assert record_entry["action"] is None
    assert "ACTION" not in record_entry["evidence_ids"]
    assert "DESCRIPTION" in record_entry["evidence_ids"]

    # Render extractive answer
    ans = render_extractive_answer(
        run_id=deps.run_id,
        mode="EVIDENCE",
        query_raw="boiler water leak",
        fetched_evidence=deps.fetched_evidence,
        state_revision=0,
    )
    assert len(ans.claims) == 1
    claim = ans.claims[0]
    assert claim.claim_type == "historical_problem"
    assert claim.supports[0].field == "DESCRIPTION"

    # Deterministic validation gate must pass
    val_res = validate_answer(ans, deps.fetched_evidence, deps.computed_receipts, deps.mode)
    assert val_res.is_valid is True
    assert val_res.errors == []


def test_corrupted_fallback_hash_rejection():
    from maintenance.answer_rendering import render_extractive_answer
    from maintenance.answer_validation import validate_answer

    cid = uuid4()
    ev_id = uuid4()
    raw = "CYL #2 INTAKE LEAKS."
    # Corrupted hash does not match sha256(raw)
    fetched = {
        ev_id: {
            "evidence_id": ev_id,
            "corpus_id": cid,
            "record_id": "aviation:1001",
            "field": "PROBLEM",
            "raw_text": raw,
            "source_sha256": "corrupted_hash" * 4,
            "text_sha256": "corrupted_hash" * 4,
        }
    }

    ans = render_extractive_answer(
        run_id=uuid4(),
        mode="EVIDENCE",
        query_raw="intake leak",
        fetched_evidence=fetched,
        state_revision=0,
    )
    val_res = validate_answer(ans, fetched, {}, "EVIDENCE")
    assert val_res.is_valid is False
    assert any("citation_source_hash_corrupted" in err for err in val_res.errors)


def test_missing_fallback_hash_rejection():
    from maintenance.answer_rendering import render_extractive_answer
    from maintenance.answer_validation import validate_answer

    cid = uuid4()
    ev_id = uuid4()
    raw = "CYL #2 INTAKE LEAKS."
    # Missing source_sha256 (empty string)
    fetched = {
        ev_id: {
            "evidence_id": ev_id,
            "corpus_id": cid,
            "record_id": "aviation:1001",
            "field": "PROBLEM",
            "raw_text": raw,
            "source_sha256": "",
            "text_sha256": "anything",
        }
    }

    ans = render_extractive_answer(
        run_id=uuid4(),
        mode="EVIDENCE",
        query_raw="intake leak",
        fetched_evidence=fetched,
        state_revision=0,
    )
    val_res = validate_answer(ans, fetched, {}, "EVIDENCE")
    assert val_res.is_valid is False
    assert any("citation_source_hash_missing" in err for err in val_res.errors)


def test_facility_description_cannot_be_cited_as_historical_action():
    import hashlib

    from maintenance.answer_validation import validate_claim
    from maintenance.contracts import Claim, SupportSpan

    cid = uuid4()
    ev_id = uuid4()
    raw = "CHILLER COMPRESSOR FAULT"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    fetched = {
        ev_id: {
            "evidence_id": ev_id,
            "corpus_id": cid,
            "record_id": "facility:5001",
            "field": "DESCRIPTION",
            "raw_text": raw,
            "source_sha256": h,
            "text_sha256": h,
        }
    }

    claim = Claim(
        claim_id="claim-act-bad",
        text='Record facility:5001 records action: "CHILLER COMPRESSOR FAULT"',
        claim_type="historical_action",
        supports=[
            SupportSpan(
                evidence_id=ev_id,
                corpus_id=cid,
                record_id="facility:5001",
                field="DESCRIPTION",
                start=0,
                end=len(raw),
                quote=raw,
                source_sha256=h,
            )
        ],
    )

    errs = validate_claim(claim, fetched, {}, "EVIDENCE")
    assert any("claim_type_field_mismatch: historical_action cannot cite DESCRIPTION" in e for e in errs)
