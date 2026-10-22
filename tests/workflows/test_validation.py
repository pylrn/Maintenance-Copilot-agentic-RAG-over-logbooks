"""Unit tests for claim-level evidence validation and release gate."""

import hashlib
from uuid import uuid4

from maintenance.answer_validation import (
    validate_claim,
    validate_span,
)
from maintenance.contracts import (
    Claim,
    SupportSpan,
)


def test_valid_log_span_passes_validation():
    ev_id = uuid4()
    raw_text = "CYL #2 INTAKE IS LEAKING. REMOVED & REPLACED GASKET."
    source_sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    fetched = {
        ev_id: {
            "evidence_id": ev_id,
            "corpus_id": uuid4(),
            "record_id": "aviation:100009",
            "field": "PROBLEM",
            "raw_text": raw_text,
            "source_sha256": source_sha256,
        }
    }

    quote = "CYL #2 INTAKE IS LEAKING."
    span = SupportSpan(
        evidence_id=ev_id,
        corpus_id=fetched[ev_id]["corpus_id"],
        record_id="aviation:100009",
        field="PROBLEM",
        start=0,
        end=len(quote),
        quote=quote,
        source_sha256=source_sha256,
    )

    errors = validate_span(span, fetched)
    assert errors == []


def test_quote_mismatch_fails_validation():
    ev_id = uuid4()
    raw_text = "CYL #2 INTAKE IS LEAKING."
    source_sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    fetched = {
        ev_id: {
            "evidence_id": ev_id,
            "corpus_id": uuid4(),
            "record_id": "aviation:100009",
            "field": "PROBLEM",
            "raw_text": raw_text,
            "source_sha256": source_sha256,
        }
    }

    span = SupportSpan(
        evidence_id=ev_id,
        corpus_id=fetched[ev_id]["corpus_id"],
        record_id="aviation:100009",
        field="PROBLEM",
        start=0,
        end=5,
        quote="CYL #4",  # mismatch with raw text "CYL #"
        source_sha256=source_sha256,
    )

    errors = validate_span(span, fetched)
    assert any("citation_quote_mismatch" in e for e in errors)


def test_forbidden_causal_upgrades_rejected_in_evidence_mode():
    ev_id = uuid4()
    raw_text = "REPLACED #2 INTAKE GASKET."
    source_sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    fetched = {
        ev_id: {
            "evidence_id": ev_id,
            "corpus_id": uuid4(),
            "record_id": "aviation:100009",
            "field": "ACTION",
            "raw_text": raw_text,
            "source_sha256": source_sha256,
        }
    }

    span = SupportSpan(
        evidence_id=ev_id,
        corpus_id=fetched[ev_id]["corpus_id"],
        record_id="aviation:100009",
        field="ACTION",
        start=0,
        end=len(raw_text),
        quote=raw_text,
        source_sha256=source_sha256,
    )

    bad_claim = Claim(
        claim_id="c1",
        text="Replacing the intake gasket permanently resolved the defect and is airworthy.",
        claim_type="historical_action",
        supports=[span],
    )

    errors = validate_claim(bad_claim, fetched, {}, mode="EVIDENCE")
    assert any("forbidden_causal_upgrade" in e for e in errors)
