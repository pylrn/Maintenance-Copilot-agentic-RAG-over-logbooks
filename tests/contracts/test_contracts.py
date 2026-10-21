from uuid import uuid4

import pytest
from pydantic import ValidationError

from maintenance.auth import IdentitySigner
from maintenance.config import Settings
from maintenance.contracts import MessageRequest, PublicEvent, SearchSpec


def test_browser_cannot_select_hypothesis_on_message_route():
    with pytest.raises(ValidationError):
        MessageRequest(
            text="hello", expected_revision=0, idempotency_key=uuid4(), mode="HYPOTHESIS"
        )


def test_arbitrary_search_filters_and_empty_query_are_rejected():
    with pytest.raises(ValidationError):
        SearchSpec(query_raw="", domain="aviation")
    with pytest.raises(ValidationError):
        SearchSpec(query_raw="leak", domain="aviation", filters={"sql": "SELECT 1"})


def test_event_forbids_private_reasoning():
    with pytest.raises(ValidationError):
        PublicEvent(run_id=uuid4(), sequence=1, type="thinking", data={})


def test_production_settings_fail_without_credentials():
    with pytest.raises(ValidationError):
        Settings(app_env="production", _env_file=None)


def test_signed_identity_is_stable_tamper_resistant_and_expiring():
    signer = IdentitySigner("x" * 40)
    owner = uuid4()
    token = signer.dumps(owner)
    assert signer.loads(token) == owner
    assert signer.loads(token + "x") is None


def test_expired_identity_is_rejected():
    signer = IdentitySigner("x" * 40, max_age=-1)
    assert signer.loads(signer.dumps(uuid4())) is None


def test_exported_fixtures_validate_against_canonical_models():
    import json
    from pathlib import Path

    from maintenance.contracts import (
        AnswerEnvelope,
        PublicEvent,
        RecordSnapshot,
        SearchResult,
        SessionSnapshot,
    )

    fixtures = Path("contracts/v1/fixtures")
    SearchResult.model_validate(json.loads((fixtures / "search.json").read_text()))
    RecordSnapshot.model_validate(json.loads((fixtures / "record.json").read_text())["record"])
    AnswerEnvelope.model_validate(json.loads((fixtures / "answer.json").read_text())["answer"])
    SessionSnapshot.model_validate(json.loads((fixtures / "session.json").read_text())["session"])
    for e in json.loads((fixtures / "events.json").read_text()):
        PublicEvent.model_validate(e)
