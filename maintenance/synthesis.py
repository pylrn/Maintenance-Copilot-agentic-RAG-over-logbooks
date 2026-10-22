"""A model selects source fields; only server-rendered, checked prose is released."""
import json
from html import escape
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

PROMPT_VERSION = "evidence-selection/v2"
INSUFFICIENT_SUMMARY = (
    "Insufficient evidence: retrieved candidates do not establish a matching complaint in the authorized records. "
    "This does not prove that the fault is absent or identify a repair."
)
NO_EVIDENCE_CONCLUSION = "No evidence found for this complaint in the historical records."
LIMITS = [
    "These historical records do not establish the cause, repair effectiveness, aircraft identity, or applicability to your aircraft.",
    "They do not supply approved maintenance instructions, operational clearance, or proof that the aircraft is safe to fly.",
]


class RecordSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    problem_evidence_id: UUID
    action_evidence_ids: list[UUID] = Field(max_length=1)


class EvidenceSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["supported_historical", "insufficient_evidence"]
    records: list[RecordSelection] = Field(max_length=2)

    @model_validator(mode="after")
    def coherent_decision(self):
        if bool(self.records) != (self.decision == "supported_historical"):
            raise ValueError("decision must agree with selected records")
        ids = [r.problem_evidence_id for r in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate source selection")
        return self


def check_selection(selection: EvidenceSelection, evidence: dict[UUID, dict[str, Any]]) -> None:
    for record in selection.records:
        problem = evidence.get(record.problem_evidence_id)
        if not problem or problem["field"] not in {"PROBLEM", "DESCRIPTION"}:
            raise ValueError("problem evidence must reference a fetched original problem/description")
        for eid in record.action_evidence_ids:
            action = evidence.get(eid)
            if (not action or action["field"] != "ACTION"
                    or action["record_id"] != problem["record_id"]
                    or str(action["corpus_id"]) != str(problem["corpus_id"])):
                raise ValueError("action must be fetched from the same record and corpus as its problem")


def default_selection(evidence: dict[UUID, dict[str, Any]]) -> EvidenceSelection:
    records = []
    seen = set()
    for eid, ev in evidence.items():
        if ev["field"] not in {"PROBLEM", "DESCRIPTION"} or not ev.get("raw_text"):
            continue
        if ev["raw_text"] in seen:
            continue
        seen.add(ev["raw_text"])
        actions = [aid for aid, action in evidence.items()
                   if action["field"] == "ACTION" and action["record_id"] == ev["record_id"]
                   and str(action["corpus_id"]) == str(ev["corpus_id"])]
        records.append(RecordSelection(problem_evidence_id=eid, action_evidence_ids=actions[:1]))
        if len(records) == 2:
            break
    return EvidenceSelection(decision="supported_historical" if records else "insufficient_evidence", records=records)


def selection_ids(selection: EvidenceSelection) -> list[UUID]:
    return [eid for r in selection.records for eid in [r.problem_evidence_id, *r.action_evidence_ids]]


def selection_from_ids(ids: list[UUID], evidence: dict[UUID, dict[str, Any]]) -> EvidenceSelection:
    subset = {}
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate synthesis source")
    for eid in ids:
        if eid not in evidence:
            raise ValueError("synthesis source not fetched")
        subset[eid] = evidence[eid]
    records = [RecordSelection(problem_evidence_id=eid, action_evidence_ids=[
        aid for aid, action in subset.items() if action["field"] == "ACTION"
        and action["record_id"] == ev["record_id"]
        and str(action["corpus_id"]) == str(ev["corpus_id"])
    ]) for eid, ev in subset.items() if ev["field"] in {"PROBLEM", "DESCRIPTION"}]
    selection = EvidenceSelection(decision="supported_historical" if records else "insufficient_evidence", records=records)
    if set(selection_ids(selection)) != set(ids):
        raise ValueError("orphan action or invalid synthesis field")
    check_selection(selection, evidence)
    return selection


def render_synthesis(selection: EvidenceSelection, evidence: dict[UUID, dict[str, Any]]) -> tuple[str, list[str], list[str]]:
    check_selection(selection, evidence)
    if selection.decision == "insufficient_evidence":
        return INSUFFICIENT_SUMMARY, [NO_EVIDENCE_CONCLUSION], list(LIMITS)
    lines = []
    for record in selection.records:
        problem = evidence[record.problem_evidence_id]
        text = f'Historical record {problem["record_id"]} reports: "{problem["raw_text"]}".'
        if record.action_evidence_ids:
            action = evidence[record.action_evidence_ids[0]]
            text += f' Its recorded action is: "{action["raw_text"]}".'
        else:
            text += " No separate corrective-action field was selected for this record."
        lines.append(text)
    return lines[0], [escape(line) for line in lines], list(LIMITS)


def synthesis_messages(query: str, evidence: dict[UUID, dict[str, Any]]) -> list[dict[str, str]]:
    system = (Path(__file__).resolve().parents[1] / "docs/prompts/evidence_selection_v2.md").read_text()
    packet = {
        "query": query,
        "evidence": [{"evidence_id": str(eid), "record_id": ev["record_id"],
                      "field": ev["field"], "raw_text": ev["raw_text"]} for eid, ev in evidence.items()],
    }
    return [{"role": "system", "content": system},
            {"role": "user", "content": json.dumps(packet, ensure_ascii=False)}]
