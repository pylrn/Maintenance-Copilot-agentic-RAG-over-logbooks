"""Claim-level evidence validation gate and semantic support checker."""

import hashlib
from typing import Any
from uuid import UUID

from maintenance.contracts import (
    AnswerEnvelope,
    Claim,
    DraftAnswer,
    Mode,
    ReceiptSupport,
    SupportSpan,
)

FORBIDDEN_CAUSAL_PHRASES = [
    "permanently resolved",
    "permanently fixed",
    "guaranteed fix",
    "approved procedure",
    "certified fix",
    "certified repair",
    "safe to fly",
    "airworthy",
    "airworthiness release",
    "will resolve your problem",
    "definitely caused by",
    "the fix is to",
    "you should replace",
    "you must replace",
]


class ValidationResult:
    def __init__(self, is_valid: bool, errors: list[str], repaired_draft: DraftAnswer | None = None):
        self.is_valid = is_valid
        self.errors = errors
        self.repaired_draft = repaired_draft

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.is_valid,
            "errors": self.errors,
            "error_count": len(self.errors),
        }


def validate_span(
    support: SupportSpan,
    fetched_evidence: dict[UUID, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    evidence = fetched_evidence.get(support.evidence_id)
    if evidence is None:
        return ["citation_not_fetched"]

    if (
        str(support.corpus_id) != str(evidence.get("corpus_id"))
        or str(support.record_id) != str(evidence["record_id"])
        or support.field != evidence["field"]
        or support.source_sha256 != evidence["source_sha256"]
    ):
        errors.append("citation_identity_mismatch")

    raw_text = evidence.get("raw_text", "")
    text_len = len(raw_text)

    if not (0 <= support.start < support.end <= text_len):
        errors.append(f"citation_offset_invalid: 0 <= {support.start} < {support.end} <= {text_len}")
        return errors

    actual_quote = raw_text[support.start:support.end]
    if actual_quote != support.quote:
        errors.append(
            f"citation_quote_mismatch: expected '{support.quote[:30]}' got '{actual_quote[:30]}'"
        )

    # Verify field hash matches raw text UTF-8 sha256 and is not missing
    computed_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    if not support.source_sha256:
        errors.append("citation_source_hash_missing")
    elif computed_hash != support.source_sha256:
        errors.append("citation_source_hash_corrupted")

    return errors


def validate_receipt_support(
    support: ReceiptSupport,
    computed_receipts: dict[UUID, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    receipt = computed_receipts.get(support.receipt_id)
    if receipt is None:
        return ["receipt_not_computed"]

    if receipt.get("kind") != support.kind:
        errors.append(f"receipt_kind_mismatch: expected {receipt.get('kind')} got {support.kind}")

    result = receipt.get("result", {})
    for key in support.result_keys:
        if key not in result:
            errors.append(f"receipt_key_missing: {key}")

    return errors


def validate_claim(
    claim: Claim,
    fetched_evidence: dict[UUID, dict[str, Any]],
    computed_receipts: dict[UUID, dict[str, Any]],
    mode: Mode,
) -> list[str]:
    errors: list[str] = []
    text_lower = claim.text.lower()

    # Check for forbidden causal and prescription upgrades in EVIDENCE / non-HYPOTHESIS modes
    if mode != "HYPOTHESIS":
        for phrase in FORBIDDEN_CAUSAL_PHRASES:
            if phrase in text_lower:
                errors.append(f"forbidden_causal_upgrade: '{phrase}' in claim '{claim.claim_id}'")

    if not claim.supports:
        errors.append(f"claim_lacks_supports: claim '{claim.claim_id}' has no citations")
        return errors

    for sup in claim.supports:
        if isinstance(sup, SupportSpan):
            span_errors = validate_span(sup, fetched_evidence)
            errors.extend(span_errors)
        elif isinstance(sup, ReceiptSupport):
            receipt_errors = validate_receipt_support(sup, computed_receipts)
            errors.extend(receipt_errors)
        else:
            errors.append(f"unknown_support_type: {type(sup)}")

    # In EVIDENCE / non-HYPOTHESIS modes:
    # Require finite approved extractive templates or exact quote-only text.
    # Field-specific templates: PROBLEM cannot be labeled action, ACTION cannot be labeled problem.
    # Fails closed if no approved templates can be formed.
    if mode != "HYPOTHESIS":
        span_supports = [s for s in claim.supports if isinstance(s, SupportSpan)]
        receipt_supports = [s for s in claim.supports if isinstance(s, ReceiptSupport)]

        valid_templates: set[str] = set()
        for sup in span_supports:
            q = sup.quote.strip()
            rid = str(sup.record_id)
            if sup.field == "PROBLEM":
                if claim.claim_type == "historical_action":
                    errors.append(f"claim_type_field_mismatch: historical_action cannot cite PROBLEM in '{claim.claim_id}'")
                valid_templates.add(f'Record {rid} records problem: "{q}"')
            elif sup.field == "DESCRIPTION":
                if claim.claim_type == "historical_action":
                    errors.append(f"claim_type_field_mismatch: historical_action cannot cite DESCRIPTION in '{claim.claim_id}'")
                valid_templates.add(f'Record {rid} records description: "{q}"')
                valid_templates.add(f'Record {rid} records problem: "{q}"')
            elif sup.field == "ACTION":
                if claim.claim_type in ("historical_problem", "historical_description"):
                    errors.append(f"claim_type_field_mismatch: {claim.claim_type} cannot cite ACTION in '{claim.claim_id}'")
                valid_templates.add(f'Record {rid} records action: "{q}"')
                valid_templates.add(f'Record {rid} records corrective action: "{q}"')
            valid_templates.add(f'Record {rid}: "{q}"')
            valid_templates.add(f'"{q}"')
            valid_templates.add(q)

        for sup in receipt_supports:
            receipt = computed_receipts.get(sup.receipt_id)
            if receipt:
                res = receipt.get("result", {})
                for k in sup.result_keys:
                    val = res.get(k)
                    if val is not None:
                        v_str = str(val).strip()
                        valid_templates.add(v_str)
                        valid_templates.add(f'Receipt {sup.kind}: "{v_str}"')
                        valid_templates.add(f'Computed {sup.kind} ({k}): {v_str}')
                        valid_templates.add(f'{k}: {v_str}')

        normalized_claim_text = claim.text.strip()
        if not valid_templates or normalized_claim_text not in valid_templates:
            errors.append(
                f"unsupported_claim_content: claim '{claim.claim_id}' must match approved extractive template or exact quote text without additional conclusion"
            )

    return errors


def validate_draft(
    draft: DraftAnswer,
    fetched_evidence: dict[UUID, dict[str, Any]],
    computed_receipts: dict[UUID, dict[str, Any]],
    mode: Mode,
) -> ValidationResult:
    all_errors: list[str] = []

    # Validate findings claims
    for claim in draft.findings:
        errs = validate_claim(claim, fetched_evidence, computed_receipts, mode)
        all_errors.extend(errs)

    # Validate historical_actions claims
    for claim in draft.historical_actions:
        errs = validate_claim(claim, fetched_evidence, computed_receipts, mode)
        all_errors.extend(errs)

    # Validate contrasting_cases claims
    for claim in draft.contrasting_cases:
        errs = validate_claim(claim, fetched_evidence, computed_receipts, mode)
        all_errors.extend(errs)

    # If draft claims historical facts but no evidence was fetched, that's invalid
    total_claims = len(draft.findings) + len(draft.historical_actions) + len(draft.contrasting_cases)
    if total_claims > 0 and not fetched_evidence and not computed_receipts:
        all_errors.append("claims_present_without_fetched_evidence")

    return ValidationResult(is_valid=(len(all_errors) == 0), errors=all_errors)


def validate_answer(
    answer: AnswerEnvelope,
    fetched_evidence: dict[UUID, dict[str, Any]],
    computed_receipts: dict[UUID, dict[str, Any]],
    mode: Mode,
) -> ValidationResult:
    all_errors: list[str] = []
    for claim in answer.claims:
        errs = validate_claim(claim, fetched_evidence, computed_receipts, mode)
        all_errors.extend(errs)

    if answer.claims and not fetched_evidence and not computed_receipts:
        all_errors.append("claims_present_without_fetched_evidence")

    return ValidationResult(is_valid=(len(all_errors) == 0), errors=all_errors)
