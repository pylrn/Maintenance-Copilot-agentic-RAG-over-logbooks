"""Registered typed tools for the Maintenance Atlas agent."""

import hashlib
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from maintenance.contracts import (
    RecordSnapshot,
    SearchResult,
    SearchSpec,
    ServiceScope,
)
from maintenance.features.visuals import VisualService


@dataclass
class RunDeps:
    owner_id: UUID
    session_id: UUID
    run_id: UUID
    mode: str
    state_revision: int
    corpus_ids: list[UUID]
    search_engine: Any
    record_service: Any
    comparison_service: Any
    pattern_service: Any
    visual_service: VisualService
    fetched_evidence: dict[UUID, dict[str, Any]]
    computed_receipts: dict[UUID, dict[str, Any]]
    tool_events: list[dict[str, Any]]
    max_tool_calls: int = 8


async def tool_search_records(
    deps: RunDeps,
    query: str,
    domain: str = "aviation",
    top_k: int = 6,
) -> dict[str, Any]:
    """Search historical maintenance records using BM25 and dense retrieval."""
    scope = ServiceScope(owner_id=deps.owner_id, corpus_ids=deps.corpus_ids)
    spec = SearchSpec(query_raw=query, domain=domain, top_k=top_k)
    res: SearchResult = await deps.search_engine.search(spec, scope)

    deps.tool_events.append(
        {
            "tool_name": "search_records",
            "summary": f"Retrieved {len(res.hits)} hits across raw/normalized BM25 and vector channels.",
            "record_ids": [h.record_id for h in res.hits],
        }
    )

    record_map = {}
    try:
        rids = [h.record_id for h in res.hits]
        if rids and hasattr(deps.search_engine, "fetch"):
            recs = await deps.search_engine.fetch(rids[:10], scope)
            record_map = {r.record_id: r for r in recs}
    except Exception:
        pass

    return {
        "search_id": str(res.search_id),
        "hit_count": len(res.hits),
        "hits": [
            {
                "record_id": h.record_id,
                "score": round(h.rrf_score, 4),
                "compatibility": h.compatibility.tier if h.compatibility else "unknown",
                "problem": record_map[h.record_id].problem_raw if h.record_id in record_map else "",
                "action": record_map[h.record_id].action_raw if h.record_id in record_map and record_map[h.record_id].action_raw else "",
            }
            for h in res.hits
        ],
    }


async def tool_get_records(
    deps: RunDeps,
    record_ids: list[str],
) -> dict[str, Any]:
    """Fetch exact raw records and register evidence snapshots for citation."""
    scope = ServiceScope(owner_id=deps.owner_id, corpus_ids=deps.corpus_ids)
    # Fetch from record service
    records: list[RecordSnapshot] = await deps.record_service.fetch(record_ids, scope)

    results = []
    for rec in records:
        evidence_ids: dict[str, str] = {}
        if rec.domain == "facility" or "DESCRIPTION" in rec.field_sha256:
            desc_id = uuid4()
            desc_source_sha = rec.field_sha256.get("DESCRIPTION", "")
            desc_computed_sha = hashlib.sha256(rec.problem_raw.encode("utf-8")).hexdigest()
            deps.fetched_evidence[desc_id] = {
                "evidence_id": desc_id,
                "corpus_id": rec.corpus_id,
                "record_id": rec.record_id,
                "field": "DESCRIPTION",
                "raw_text": rec.problem_raw,
                "source_sha256": desc_source_sha,
                "text_sha256": desc_computed_sha,
            }
            evidence_ids["DESCRIPTION"] = str(desc_id)
            results.append(
                {
                    "record_id": rec.record_id,
                    "source_id": rec.source_id,
                    "description": rec.problem_raw,
                    "action": None,
                    "evidence_ids": evidence_ids,
                }
            )
        else:
            prob_id = uuid4()
            prob_source_sha = rec.field_sha256.get("PROBLEM", "")
            prob_computed_sha = hashlib.sha256(rec.problem_raw.encode("utf-8")).hexdigest()
            deps.fetched_evidence[prob_id] = {
                "evidence_id": prob_id,
                "corpus_id": rec.corpus_id,
                "record_id": rec.record_id,
                "field": "PROBLEM",
                "raw_text": rec.problem_raw,
                "source_sha256": prob_source_sha,
                "text_sha256": prob_computed_sha,
            }
            evidence_ids["PROBLEM"] = str(prob_id)

            if rec.action_raw:
                act_id = uuid4()
                act_source_sha = rec.field_sha256.get("ACTION", "")
                act_computed_sha = hashlib.sha256(rec.action_raw.encode("utf-8")).hexdigest()
                deps.fetched_evidence[act_id] = {
                    "evidence_id": act_id,
                    "corpus_id": rec.corpus_id,
                    "record_id": rec.record_id,
                    "field": "ACTION",
                    "raw_text": rec.action_raw,
                    "source_sha256": act_source_sha,
                    "text_sha256": act_computed_sha,
                }
                evidence_ids["ACTION"] = str(act_id)

            results.append(
                {
                    "record_id": rec.record_id,
                    "source_id": rec.source_id,
                    "problem": rec.problem_raw,
                    "action": rec.action_raw or "",
                    "evidence_ids": evidence_ids,
                }
            )

    deps.tool_events.append(
        {
            "tool_name": "get_records",
            "summary": f"Fetched {len(records)} authoritative records with exact fields and hashes.",
            "record_ids": [r.record_id for r in records],
        }
    )

    return {"records": results}


async def tool_compare_records(
    deps: RunDeps,
    record_ids: list[str],
) -> dict[str, Any]:
    """Compare grounded problem and action text between 2 to 6 fetched records."""
    if not deps.comparison_service:
        return {"error": "comparison_service_unavailable"}
    scope = ServiceScope(owner_id=deps.owner_id, corpus_ids=deps.corpus_ids)
    receipt = await deps.comparison_service.compare(record_ids, scope)

    receipt_id = uuid4()
    deps.computed_receipts[receipt_id] = {
        "receipt_id": receipt_id,
        "kind": "comparison",
        "parameters": receipt.parameters,
        "result": receipt.result,
        "corpus_ids": receipt.corpus_ids,
        "manifest_sha256": receipt.manifest_sha256,
        "contributing_ids": receipt.contributing_ids,
    }

    deps.tool_events.append(
        {
            "tool_name": "compare_records",
            "summary": f"Compared {len(record_ids)} records on grounded spans.",
            "record_ids": record_ids,
        }
    )

    return {"receipt_id": str(receipt_id), "result": receipt.result}


async def tool_get_pattern_summary(
    deps: RunDeps,
    component: str,
    domain: str = "aviation",
) -> dict[str, Any]:
    """Retrieve recurring corpus pattern counts and distinct problem/action groups."""
    if not deps.pattern_service:
        return {"error": "pattern_service_unavailable"}
    scope = ServiceScope(owner_id=deps.owner_id, corpus_ids=deps.corpus_ids)
    filters = {"component": component, "domain": domain}
    receipt = await deps.pattern_service.summarize(filters, scope)

    receipt_id = uuid4()
    deps.computed_receipts[receipt_id] = {
        "receipt_id": receipt_id,
        "kind": "aggregate",
        "parameters": receipt.parameters,
        "result": receipt.result,
        "corpus_ids": receipt.corpus_ids,
        "manifest_sha256": receipt.manifest_sha256,
        "contributing_ids": receipt.contributing_ids,
    }

    deps.tool_events.append(
        {
            "tool_name": "get_pattern_summary",
            "summary": f"Calculated recurring pattern count for '{component}'.",
            "record_ids": receipt.contributing_ids[:5],
        }
    )

    return {"receipt_id": str(receipt_id), "result": receipt.result}


async def tool_get_component_context(
    deps: RunDeps,
    component_id: str,
) -> dict[str, Any]:
    """Retrieve reviewed educational background and 2D visual mapping hotspots."""
    envelope = deps.visual_service.get_component_context(component_id)
    deps.tool_events.append(
        {
            "tool_name": "get_component_context",
            "summary": f"Loaded educational context and visual mappings for '{envelope.name}'.",
            "record_ids": [],
        }
    )
    return envelope.model_dump(mode="json")
