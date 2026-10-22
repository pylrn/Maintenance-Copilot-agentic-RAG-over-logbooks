import hashlib
import json
from collections import defaultdict

from maintenance.contracts import ComputationReceipt, SearchFilters
from maintenance.ingest.annotate import mentions


def receipt(kind, parameters, result, records, scope):
    ids = sorted(f"{r.corpus_id}/{r.record_id}/{r.source_file_sha256}" for r in records)
    canonical = json.dumps(
        {
            "kind": kind,
            "parameters": parameters,
            "result": result,
            "ids": ids,
            "corpus_ids": sorted(map(str, scope.corpus_ids)),
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return ComputationReceipt(
        kind=kind,
        parameters=parameters,
        result=result,
        corpus_ids=scope.corpus_ids,
        manifest_sha256=hashlib.sha256(canonical.encode()).hexdigest(),
        contributing_ids=ids,
    )


class PatternService:
    def __init__(self, engine):
        self.engine = engine

    async def summarize(self, filters, scope):
        filters = SearchFilters.model_validate(filters)
        rows = []
        for r in self.engine.scoped_records(scope):
            tags = {m.value for m in mentions(r.problem_raw)}
            if filters.component and filters.component not in tags:
                continue
            if filters.symptom and filters.symptom not in tags:
                continue
            rows.append(r)
        groups = defaultdict(list)
        for r in rows:
            groups[(str(r.corpus_id), r.duplicate_key)].append(r.record_id)
        result = {
            "raw_rows": len(rows),
            "distinct_pairs": len(groups),
            "duplicate_policy": "exact raw problem/action pair within corpus",
            "scope": "corpus patterns, not repeated defects on a known aircraft",
            "groups": [
                {"representative": sorted(ids)[0], "raw_rows": len(ids), "record_ids": sorted(ids)}
                for _, ids in sorted(groups.items())
            ],
        }
        return receipt("aggregate", filters.model_dump(), result, rows, scope)
