import re

from maintenance.contracts import Compatibility
from maintenance.ingest.annotate import mentions


def assess(query: str, problem: str) -> Compatibility:
    qm, sm = mentions(query), mentions(problem)
    facts = {}
    for name in ["component", "symptom", "laterality", "cylinder_number", "engine_number"]:
        q = {m.value for m in qm if m.kind == name}
        s = {m.value for m in sm if m.kind == name}
        facts[name] = "unknown" if not q or not s else "agreement" if q & s else "difference"
    # Unqualified #N is comparable as a number mention, not assigned to an engine/cylinder.
    q = {m.value for m in qm if "number" in m.kind}
    s = {m.value for m in sm if "number" in m.kind}
    facts["number"] = "unknown" if not q or not s else "agreement" if q & s else "difference"
    typed = {"cylinder_number", "engine_number"}
    qk = {m.kind for m in qm if m.kind in typed}
    sk = {m.kind for m in sm if m.kind in typed}
    facts["number_context"] = (
        "unknown" if not qk or not sk else "agreement" if qk & sk else "difference"
    )

    def negated_symptoms(text, ms):
        return {
            m.value
            for m in ms
            if m.kind == "symptom"
            and re.search(
                r"\b(no|not|without|never)\s+(?:\w+\s+){0,2}$",
                text[max(0, m.start - 25) : m.start],
                re.IGNORECASE,
            )
        }

    qsym = {m.value for m in qm if m.kind == "symptom"}
    ssym = {m.value for m in sm if m.kind == "symptom"}
    shared = qsym & ssym
    facts["negation"] = (
        "difference"
        if (negated_symptoms(query, qm) ^ negated_symptoms(problem, sm)) & shared
        else "agreement"
        if shared
        else "unknown"
    )
    conflict = any(v == "difference" for v in facts.values())
    direct = facts["component"] == "agreement" and facts["symptom"] == "agreement" and not conflict
    related = facts["component"] == "agreement" or facts["symptom"] == "agreement"
    return Compatibility(
        tier="direct" if direct else "related" if related else "tangential",
        facts=facts,
        query_mentions=qm,
        source_mentions=sm,
        limitations=["heuristic relevance; source aircraft applicability unknown"],
    )
