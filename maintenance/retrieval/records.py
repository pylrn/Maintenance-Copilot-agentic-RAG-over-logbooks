"""Authoritative source lookup, including versions no longer in the active index."""

from maintenance.contracts import RecordSnapshot
from maintenance.ingest.manifest import truncation_annotations


class RecordService:
    def __init__(self, database):
        self.database = database

    async def fetch(self, record_ids, scope):
        if not 1 <= len(record_ids) <= 10:
            raise ValueError("fetch batch must contain 1–10 IDs")
        async with self.database.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT r.*,c.domain,c.sha256 FROM maintenance_records r JOIN corpus_versions c USING(corpus_id) WHERE r.corpus_id=ANY($1::uuid[]) AND r.record_id=ANY($2::text[])",
                scope.corpus_ids,
                record_ids,
            )
        found = []
        for rid in record_ids:
            matches = [row for row in rows if row["record_id"] == rid]
            if len(matches) != 1:
                raise LookupError("source missing or ambiguous version")
            data = dict(matches[0])
            annotations = dict(data.pop("annotations"))
            fields = annotations.pop("field_sha256")
            annotations.update(
                truncation_annotations(data["problem_raw"], data["action_raw"], data["domain"])
            )
            digest = data.pop("sha256")
            found.append(
                RecordSnapshot(
                    **data, annotations=annotations, field_sha256=fields, source_file_sha256=digest
                )
            )
        return found
