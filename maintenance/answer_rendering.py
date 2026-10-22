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
    summary: str | None = None,
    what_can_be_concluded: list[str] | None = None,
    what_cannot_be_concluded: list[str] | None = None,
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
        no_ev_summary = summary or "No historical maintenance records found matching this fault complaint."
        no_ev_can = what_can_be_concluded or [
            "No evidence found for this complaint in the historical records."
        ]
        no_ev_cannot = what_cannot_be_concluded or [
            "Cannot conclude component involvement, defect mechanism, or corrective actions due to lack of matching records in the authorized dataset."
        ]
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
            summary=no_ev_summary,
            what_can_be_concluded=no_ev_can,
            what_cannot_be_concluded=no_ev_cannot,
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
    # Group identical problems to avoid redundant duplicate bullets
    prob_quotes_map: dict[str, list[SupportSpan]] = {}
    for rec_id, fields in records_map.items():
        prob = fields.get("PROBLEM") or fields.get("DESCRIPTION")
        if prob and prob.get("raw_text"):
            full_raw = prob["raw_text"]
            quote = full_raw.strip()
            if quote:
                start = full_raw.find(quote)
                end = start + len(quote)
                span = SupportSpan(
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
                prob_quotes_map.setdefault(quote, []).append(span)

    for quote, supports in prob_quotes_map.items():
        rep_rec = supports[0].record_id
        field_name = supports[0].field
        field_label = "description" if field_name == "DESCRIPTION" else "problem"
        claims.append(
            Claim(
                claim_id=f"claim-prob-{claim_idx}",
                text=f'Record {rep_rec} records {field_label}: "{quote}"',
                claim_type="historical_problem",
                supports=supports,
            )
        )
        claim_idx += 1

    # Group identical actions to avoid redundant duplicate bullets
    act_quotes_map: dict[str, list[SupportSpan]] = {}
    for rec_id, fields in records_map.items():
        act = fields.get("ACTION")
        if act and act.get("raw_text"):
            full_raw = act["raw_text"]
            quote = full_raw.strip()
            if quote:
                start = full_raw.find(quote)
                end = start + len(quote)
                span = SupportSpan(
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
                act_quotes_map.setdefault(quote, []).append(span)

    for quote, supports in act_quotes_map.items():
        rep_rec = supports[0].record_id
        claims.append(
            Claim(
                claim_id=f"claim-act-{claim_idx}",
                text=f'Record {rep_rec} records corrective action: "{quote}"',
                claim_type="historical_action",
                supports=supports,
            )
        )
        claim_idx += 1

    unique_recs = sorted(list(set(fetched_record_ids)))
    headline = f"Found {len(unique_recs)} relevant historical maintenance record(s) matching complaint."

    visual_refs = []
    q_lower = query_raw.lower()
    if "intake" in q_lower or "gasket" in q_lower:
        visual_refs.extend(["intake_system", "intake_gasket"])
    if "cylinder" in q_lower or "cyl" in q_lower:
        visual_refs.extend(["cylinder_assembly"])
    if "rocker" in q_lower:
        visual_refs.extend(["rocker_cover"])
    if ("engine" in q_lower or "oil" in q_lower) and not visual_refs:
        visual_refs.extend(["engine_left", "intake_system"])

    allowed_actions = build_allowed_actions(answer_id, state_revision, unique_recs, mode)

    # Dynamic synthesis of conclusions and summary directly from actual retrieved evidence
    if not what_can_be_concluded:
        what_can_be_concluded = []
        distinct_acts = list(act_quotes_map.keys())
        if distinct_acts:
            cleaned_acts = []
            for a in distinct_acts[:3]:
                c = a.strip().rstrip(".")
                if c:
                    cleaned_acts.append(f"<strong>{c}</strong>")
            if cleaned_acts:
                what_can_be_concluded.append(
                    f"Technicians responding to these complaints documented corrective actions including: {', '.join(cleaned_acts)}."
                )
            checks = [
                a for a in distinct_acts
                if any(k in a.upper() for k in ["LEAK", "CHECK", "CK", "RAN", "OPS", "TEST"])
            ]
            if checks:
                what_can_be_concluded.append(
                    f"Post-maintenance operational runs and leak checks were recorded in history (e.g. <code>{checks[0][:60]}</code>)."
                )
        if not what_can_be_concluded:
            what_can_be_concluded.append(
                f"Historical records confirm recorded maintenance activity associated with complaint terms across {len(unique_recs)} case(s)."
            )

    if not what_cannot_be_concluded:
        what_cannot_be_concluded = [
            "MaintNet research records omit specific airframe/engine serial applicability; historical records do not certify applicability to your specific aircraft.",
            "Historical log entries document past technician actions as written; they do not replace approved Aircraft Maintenance Manual (AMM) procedures or guarantee permanent root-cause elimination.",
        ]

    if not summary:
        distinct_probs = list(prob_quotes_map.keys())
        prob_desc = f'"{distinct_probs[0][:60]}"' if distinct_probs else query_raw
        act_summary = (
            f'with recorded corrective actions such as "{list(act_quotes_map.keys())[0][:50]}"'
            if act_quotes_map
            else "with recorded historical maintenance interventions."
        )
        summary = f"Based on {len(unique_recs)} distinct matching log record(s), historical complaints report {prob_desc} {act_summary}."

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
        summary=summary,
        what_can_be_concluded=what_can_be_concluded,
        what_cannot_be_concluded=what_cannot_be_concluded,
    )
