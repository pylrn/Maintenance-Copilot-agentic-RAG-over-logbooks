"""Conservative complaint support gate; search relevance alone is not proof."""
from typing import Any
from uuid import UUID

from maintenance.ingest.annotate import mentions
from maintenance.retrieval.compatibility import assess


def supporting_evidence(query: str, evidence: dict[UUID, dict[str, Any]]) -> dict[UUID, dict[str, Any]]:
    """Keep whole records only when their problem covers all recognized query facets.

    This deliberately abstains for unrecognized complaints. Actions cannot establish
    a symptom match, and matching facets across different records is not allowed.
    """
    query_mentions = mentions(query)
    facets = {}
    for kind in ("component", "symptom", "laterality", "cylinder_number", "engine_number", "number"):
        values = {m.value for m in query_mentions if m.kind == kind}
        if values:
            facets[kind] = values
    if "component" not in facets or "symptom" not in facets:
        return {}

    matching = set()
    for ev in evidence.values():
        if ev["field"] not in {"PROBLEM", "DESCRIPTION"}:
            continue
        raw = ev["raw_text"]
        source_mentions = mentions(raw)
        if any(fact == "difference" for fact in assess(query, raw).facts.values()):
            continue
        if all(values <= {m.value for m in source_mentions if m.kind == kind}
               for kind, values in facets.items()):
            matching.add(str(ev["record_id"]))
    return {eid: ev for eid, ev in evidence.items() if str(ev["record_id"]) in matching}
