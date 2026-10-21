import re

from maintenance.features.patterns import receipt
from maintenance.ingest.annotate import mentions
from maintenance.ingest.normalize import normalize


class SensitivityService:
    def __init__(self, engine):
        self.engine = engine

    async def compare_specs(self, base_spec, variants, scope):
        if not 1 <= len(variants) <= 3:
            raise ValueError("one to three variants required")
        changes = []
        for v in variants:
            original = base_spec.model_dump(exclude={"query_raw", "query_normalized"})
            changed = v.model_dump(exclude={"query_raw", "query_normalized"})
            if original != changed or v.query_raw == base_spec.query_raw:
                raise ValueError("only the disclosed query text may change")
            base = base_spec.query_raw
            other = v.query_raw
            base_neg = [m.value for m in mentions(base) if m.kind == "negation"]
            other_neg = [m.value for m in mentions(other) if m.kind == "negation"]
            if base_neg != other_neg:
                raise ValueError("negation perturbation forbidden")

            def without_number(s):
                return " ".join(
                    re.sub(r"(?i)\b(?:cyl(?:inder)?|eng(?:ine)?)\s*#?\s*\d+|#\s*\d+", "", s).split()
                )

            def without_component(s):
                return " ".join(
                    re.sub(
                        r"(?i)\b(?:intake|induction|rocker\s+(?:box\s+)?cover|baffle|battery|brake|magneto)\b",
                        "<component>",
                        s,
                    ).split()
                )

            if other == normalize(base, base_spec.domain):
                kind = "normalization"
            elif without_number(base) == other.strip():
                kind = "number_removed"
            elif without_component(base) == without_component(other):
                kind = "component_changed"
            else:
                raise ValueError("variant must change one approved dimension")
            changes.append(kind)
        searches = [
            await self.engine.search(s.model_copy(update={"top_k": 5}), scope)
            for s in [base_spec, *variants]
        ]
        baseline = [h.record_id for h in searches[0].hits]
        comparisons = []
        for kind, s in zip(changes, searches[1:], strict=True):
            ids = [h.record_id for h in s.hits]
            comparisons.append(
                {
                    "change": kind,
                    "query_raw": s.spec.query_raw,
                    "search_id": str(s.search_id),
                    "top5": ids,
                    "overlap": len(set(baseline) & set(ids)),
                    "gained": sorted(set(ids) - set(baseline)),
                    "lost": sorted(set(baseline) - set(ids)),
                    "rank_deltas": {
                        rid: ids.index(rid) - baseline.index(rid)
                        for rid in set(ids) & set(baseline)
                    },
                }
            )
        return receipt(
            "search_comparison",
            {
                "base_query": base_spec.query_raw,
                "variants": [s.query_raw for s in variants],
                "pipeline": searches[0].versions,
            },
            {
                "base_search_id": str(searches[0].search_id),
                "base_top5": baseline,
                "comparisons": comparisons,
                "meaning": "Retrieval sensitivity only; no diagnosis probability.",
            },
            list(self.engine.scoped_records(scope)),
            scope,
        )
