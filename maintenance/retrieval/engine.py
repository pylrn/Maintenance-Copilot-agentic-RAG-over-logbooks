"""Shared read-only search engine. No session writes, provider calls, or answer synthesis."""

import asyncio
import time
from uuid import UUID

from maintenance.contracts import SearchHit, SearchResult, SearchSpec, ServiceScope
from maintenance.ingest.normalize import normalize
from maintenance.retrieval.bm25 import BM25Index
from maintenance.retrieval.compatibility import assess
from maintenance.retrieval.dense import exact_cosine, normalized_matrix
from maintenance.retrieval.fusion import fuse_ranked_ids

WEIGHTS = {"bm25_raw": 0.5, "bm25_normalized": 0.5, "dense": 1.0}


class RetrievalEngine:
    def __init__(
        self, corpora, vectors, encoder, reranker=None, channels=None, use_compatibility=True
    ):
        self.corpora = {str(c.manifest.corpus_id): c for c in corpora}
        self.encoder = encoder
        self.reranker = reranker
        self.channels = set(channels or WEIGHTS)
        self.use_compatibility = use_compatibility
        self.matrices = {}
        self.indexes = {}
        self._cpu = asyncio.Semaphore(1)
        for cid, corpus in self.corpora.items():
            for representation in ["problem", "problem_action"]:
                key = cid if representation == "problem" else cid + ":problem_action"
                if key not in vectors:
                    if representation == "problem":
                        raise ValueError("missing dense index")
                    continue
                matrix = normalized_matrix(vectors[key], encoder.dimension)
                if len(matrix) != len(corpus.records):
                    raise ValueError("embedding record-count mismatch")
                self.matrices[key] = matrix
                raw = [
                    r.problem_raw
                    + ("\n" + (r.action_raw or "") if representation == "problem_action" else "")
                    for r in corpus.records
                ]
                norm = [normalize(t, corpus.manifest.domain) for t in raw]
                self.indexes[key] = (BM25Index(raw), BM25Index(norm))

    def _ids(self, spec, scope):
        ids = [str(x) for x in (spec.corpus_ids or scope.corpus_ids)]
        if not set(ids) <= set(map(str, scope.corpus_ids)):
            raise PermissionError("corpus outside authorized scope")
        if any(cid not in self.corpora for cid in ids):
            raise LookupError("corpus not available")
        return [cid for cid in ids if self.corpora[cid].manifest.domain == spec.domain]

    async def fetch(self, record_ids, scope):
        if not 1 <= len(record_ids) <= 10:
            raise ValueError("fetch batch must contain 1–10 IDs")
        found = []
        for rid in record_ids:
            matches = [
                r
                for cid in map(str, scope.corpus_ids)
                if cid in self.corpora
                for r in self.corpora[cid].records
                if r.record_id == rid
            ]
            if len(matches) != 1:
                raise LookupError("source missing or ambiguous corpus version")
            found.append(matches[0].model_copy(deep=True))
        return found

    def scoped_records(self, scope):
        for cid in map(str, scope.corpus_ids):
            if cid not in self.corpora:
                raise LookupError("corpus not available")
            yield from self.corpora[cid].records

    async def search(self, spec: SearchSpec, scope: ServiceScope):
        start = time.perf_counter()
        ids = self._ids(spec, scope)
        if not ids:
            raise LookupError("domain not available in scope")
        # Ignore browser supplied normalized text/annotations; derive from raw query.
        from maintenance.ingest.annotate import mentions

        ms = mentions(spec.query_raw)
        spec = spec.model_copy(
            update={
                "query_normalized": normalize(spec.query_raw, spec.domain),
                "corpus_ids": [UUID(cid) for cid in ids],
                "explicit_components": [m for m in ms if m.kind == "component"],
                "symptoms": [m for m in ms if m.kind == "symptom"],
                "number_mentions": [m for m in ms if "number" in m.kind],
                "negation_spans": [m for m in ms if m.kind == "negation"],
                "location_mentions": [m for m in ms if m.kind == "laterality"],
            }
        )
        representation = "problem_action" if spec.intent == "action_history" else "problem"
        async with self._cpu:
            query = (
                await asyncio.to_thread(self.encoder.encode_queries, [spec.query_normalized])
                if "dense" in self.channels
                else None
            )
            embedding_ms = (time.perf_counter() - start) * 1000
            result = await asyncio.to_thread(self._retrieve, spec, ids, representation, query)
            if spec.quality_mode:
                if self.reranker is None:
                    result.degraded_branches.append("reranker_unavailable")
                else:
                    pool = result.hits[:20]
                    rows = {f"{r.corpus_id}/{r.record_id}": r for r in self.scoped_records(scope)}
                    pairs = [
                        (spec.query_raw, rows[f"{h.corpus_id}/{h.record_id}"].problem_raw)
                        for h in pool
                    ]
                    scores = await asyncio.to_thread(self.reranker.score, pairs)
                    for h, score in zip(pool, scores, strict=True):
                        h.reranker_score = float(score)
                    order = {"direct": 0, "related": 1, "tangential": 2}
                    result.hits = sorted(
                        pool,
                        key=lambda h: (order[h.compatibility.tier], -h.reranker_score, h.record_id),
                    )
        result.hits = result.hits[: spec.top_k]
        result.timings_ms = {
            "embedding": embedding_ms,
            "total": (time.perf_counter() - start) * 1000,
        }
        return result

    def _retrieve(self, spec, ids, representation, query):
        channel_rows = {name: [] for name in self.channels}
        records = {}
        for cid in ids:
            key = cid if representation == "problem" else cid + ":problem_action"
            if key not in self.matrices:
                raise LookupError("requested representation not built")
            corpus = self.corpora[cid]
            raw, norm = self.indexes[key]
            eligible = []
            for i, r in enumerate(corpus.records):
                comp = assess(spec.query_raw, r.problem_raw)
                values = {m.value for m in comp.source_mentions}
                if spec.filters.component and spec.filters.component not in values:
                    continue
                if spec.filters.symptom and spec.filters.symptom not in values:
                    continue
                eligible.append(i)
                records[f"{cid}/{r.record_id}"] = (r, comp)
            eligible_set = set(eligible)
            # Filter first, then score; overfetch lexical hits to honor hard filters.
            paths = {}
            if "bm25_raw" in self.channels:
                paths["bm25_raw"] = raw.search(spec.query_raw, len(corpus.records))
            if "bm25_normalized" in self.channels:
                paths["bm25_normalized"] = norm.search(spec.query_normalized, len(corpus.records))
            if "dense" in self.channels:
                paths["dense"] = exact_cosine(self.matrices[key], query[0], len(corpus.records))
            for name, rows in paths.items():
                channel_rows[name].extend(
                    [
                        (f"{cid}/{corpus.records[i].record_id}", score)
                        for i, score in rows
                        if i in eligible_set
                    ][:50]
                )
        channels = {
            name: [rid for rid, score in sorted(rows, key=lambda x: (-x[1], x[0]))[:50]]
            for name, rows in channel_rows.items()
        }
        scores = {name: dict(rows) for name, rows in channel_rows.items()}
        fused = fuse_ranked_ids(channels, WEIGHTS)
        order = {"direct": 0, "related": 1, "tangential": 2}
        if self.use_compatibility:
            fused.sort(
                key=lambda h: (
                    order[records[h["record_id"]][1].tier],
                    -h["rrf_score"],
                    h["record_id"],
                )
            )
        # Exact source-pair duplicates only; all original IDs remain available.
        duplicates = {}
        for cid in ids:
            for r in self.corpora[cid].records:
                duplicates.setdefault((cid, r.duplicate_key), []).append(r.record_id)
        seen = set()
        hits = []
        for h in fused:
            r, comp = records[h["record_id"]]
            group = (str(r.corpus_id), r.duplicate_key)
            if spec.collapse_duplicates and group in seen:
                continue
            seen.add(group)
            members = sorted(duplicates[group])
            hits.append(
                SearchHit(
                    corpus_id=r.corpus_id,
                    record_id=r.record_id,
                    rrf_score=h["rrf_score"],
                    channel_ranks=h["channel_ranks"],
                    channel_scores={
                        name: scores[name][h["record_id"]] for name in h["channel_ranks"]
                    },
                    compatibility=comp,
                    duplicate_ids=members,
                    duplicate_count=len(members),
                )
            )
        public_channels = {
            name: [records[rid][0].record_id for rid in rids] for name, rids in channels.items()
        }
        return SearchResult(
            spec=spec,
            hits=hits[:20],
            channels=public_channels,
            versions={
                "pipeline": "hybrid/v1",
                "normalizer": "reviewed/v1",
                "embedding_model": self.encoder.model_id,
                "embedding_revision": self.encoder.revision,
                "representation": representation,
                "corpora": ",".join(ids),
            },
            timings_ms={},
            limitations=[
                "Historical model applicability and repair outcome are unspecified.",
                "Ranking scores are relevance signals, not diagnostic probabilities.",
            ],
        )
