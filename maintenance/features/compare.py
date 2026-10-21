from maintenance.contracts import EvidenceSpan
from maintenance.features.patterns import receipt


class ComparisonService:
    def __init__(self, engine):
        self.engine = engine

    async def compare(self, record_ids, scope):
        if not 2 <= len(record_ids) <= 6 or len(set(record_ids)) != len(record_ids):
            raise ValueError("comparison requires 2–6 distinct IDs")
        rows = await self.engine.fetch(record_ids, scope)
        entries = []
        for r in rows:
            fields = ["PROBLEM", "ACTION"] if r.domain == "aviation" else ["DESCRIPTION"]
            spans = []
            for field in fields:
                raw = r.original_fields[field]
                if raw:
                    spans.append(
                        EvidenceSpan(
                            corpus_id=r.corpus_id,
                            record_id=r.record_id,
                            field=field,
                            start=0,
                            end=len(raw),
                            quote=raw,
                            source_sha256=r.field_sha256[field],
                        ).model_dump(mode="json")
                    )
            entries.append(
                {
                    "record_id": r.record_id,
                    "source_spans": spans,
                    "action_available": r.action_raw is not None,
                    "applicability": "unknown",
                }
            )
        return receipt(
            "comparison",
            {"record_ids": record_ids},
            {
                "records": entries,
                "interpretation": "Source wording differences, not contradictions or diagnosis.",
            },
            rows,
            scope,
        )
