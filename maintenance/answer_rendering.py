"""Deterministic templates, extractive fallback synthesis, and envelope builder."""

from typing import Any
from uuid import UUID, uuid4

from maintenance.contracts import (
    AllowedAction,
    AnswerEnvelope,
    AnswerStatus,
    Claim,
    Mode,
    SupportSpan,
)


def build_allowed_actions(
    answer_id: UUID,
    state_revision: int,
    fetched_record_ids: list[str],
    mode: Mode,
) -> list[AllowedAction]:
    actions: list[AllowedAction] = []
    # Hypothesis is available after a released evidence answer
    if mode in {"EVIDENCE", "CHALLENGE", "DISTINGUISH", "SENSITIVITY"}:
        actions.append(
            AllowedAction(
                action="hypothesis",
                parent_answer_id=answer_id,
                state_revision=state_revision,
            )
        )
        actions.append(
            AllowedAction(
                action="challenge",
                parent_answer_id=answer_id,
                state_revision=state_revision,
            )
        )
        actions.append(
            AllowedAction(
                action="sensitivity",
                parent_answer_id=answer_id,
                state_revision=state_revision,
            )
        )
        actions.append(
            AllowedAction(
                action="handover",
                parent_answer_id=answer_id,
                state_revision=state_revision,
            )
        )
        if len(set(fetched_record_ids)) >= 2:
            actions.append(
                AllowedAction(
                    action="distinguish",
                    parent_answer_id=answer_id,
                    state_revision=state_revision,
                )
            )
    return actions


def render_extractive_answer(
    run_id: UUID,
    mode: Mode,
    query_raw: str,
    fetched_evidence: dict[UUID, dict[str, Any]],
    state_revision: int,
    status: AnswerStatus | None = None,
    limitations: list[str] | None = None,
    missing: list[str] | None = None,
    clarification: str | None = None,
) -> AnswerEnvelope:
    """Builds a strictly grounded extractive answer directly from validated evidence snapshots."""
    answer_id = uuid4()
    claims: list[Claim] = []
    fetched_record_ids: list[str] = []

    limitations = limitations or [
        "Historical maintenance records lack operational context and model identity; applicability to your aircraft is not certified.",
        "Maintenance records report historical actions as written and do not guarantee repair success or approved procedure.",
    ]
    missing = missing or []

    # If no evidence was fetched, return insufficient_evidence or clarification_needed
    if not fetched_evidence:
        final_status: AnswerStatus = status or "insufficient_evidence"
        headline = (
            "No historical maintenance records found matching this fault complaint."
            if final_status == "insufficient_evidence"
            else "Clarification needed to search historical maintenance records."
        )
        missing.append("No matching records found in authorized corpus.")
        return AnswerEnvelope(
            answer_id=answer_id,
            run_id=run_id,
            mode=mode,
            status=final_status,
            headline=headline,
            claims=[],
            limitations=limitations,
            missing=missing,
            clarification=clarification,
            visual_refs=[],
            allowed_actions=[],
        )

    # Group evidence by record
    records_map: dict[str, dict[str, dict[str, Any]]] = {}
    for ev_id, ev in fetched_evidence.items():
        rec_id = str(ev["record_id"])
        fetched_record_ids.append(rec_id)
        if rec_id not in records_map:
            records_map[rec_id] = {}
        records_map[rec_id][ev["field"]] = {**ev, "evidence_id": ev_id}

    claim_idx = 1
    # Build findings from PROBLEM fields
    for rec_id, fields in records_map.items():
        prob = fields.get("PROBLEM") or fields.get("DESCRIPTION")
        if prob:
            full_raw = prob["raw_text"]
            quote = full_raw.strip()
            if quote:
                start = full_raw.find(quote)
                end = start + len(quote)
                field_label = "description" if prob["field"] == "DESCRIPTION" else "problem"
                claim = Claim(
                    claim_id=f"claim-prob-{claim_idx}",
                    text=f'Record {rec_id} records {field_label}: "{quote}"',
                    claim_type="historical_problem",
                    supports=[
                        SupportSpan(
                            evidence_id=prob["evidence_id"],
                            corpus_id=prob["corpus_id"],
                            record_id=rec_id,
                            field=prob["field"],
                            start=start,
                            end=end,
                            quote=quote,
                            source_sha256=prob["source_sha256"],
                            support_kind="direct_quote",
                        )
                    ],
                )
                claims.append(claim)

        act = fields.get("ACTION")
        if act and act["raw_text"]:
            full_raw = act["raw_text"]
            quote = full_raw.strip()
            if quote:
                start = full_raw.find(quote)
                end = start + len(quote)
                claim = Claim(
                    claim_id=f"claim-act-{claim_idx}",
                    text=f"Record {rec_id} records corrective action: \"{quote}\"",
                    claim_type="historical_action",
                    supports=[
                        SupportSpan(
                            evidence_id=act["evidence_id"],
                            corpus_id=act["corpus_id"],
                            record_id=rec_id,
                            field=act["field"],
                            start=start,
                            end=end,
                            quote=quote,
                            source_sha256=act["source_sha256"],
                            support_kind="direct_quote",
                        )
                    ],
                )
                claims.append(claim)

        claim_idx += 1

    unique_recs = sorted(list(set(fetched_record_ids)))
    headline = f"Found {len(unique_recs)} relevant historical maintenance record(s) matching complaint."

    visual_refs = []
    q_lower = query_raw.lower()
    if "intake" in q_lower or "gasket" in q_lower:
        visual_refs.extend(["intake_system", "intake_gasket"])
    elif "cylinder" in q_lower or "cyl" in q_lower:
        visual_refs.extend(["cylinder_assembly"])
    elif "rocker" in q_lower:
        visual_refs.extend(["rocker_cover"])

    allowed_actions = build_allowed_actions(answer_id, state_revision, unique_recs, mode)

    return AnswerEnvelope(
        answer_id=answer_id,
        run_id=run_id,
        mode=mode,
        status="supported_historical",
        headline=headline,
        claims=claims,
        limitations=limitations,
        missing=missing,
        clarification=clarification,
        visual_refs=visual_refs,
        allowed_actions=allowed_actions,
    )
