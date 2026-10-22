"""Shared read-only search engine. No session writes, provider calls, or answer synthesis."""

import asyncio
import time
from uuid import UUID

from maintenance.contracts import (
    SearchHit,
    SearchResult,
    SearchSpec,
    SearchTrace,
    ServiceScope,
    StageTrace,
)
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
        self._reranker_busy = False
        self._projection_cache = {}
        self._projection_lock = asyncio.Lock()
        self._query_cache = {}
        self._source_mentions = {}
        self._source_components = {}
        self._source_symptoms = {}
        self._duplicates = {}

        from maintenance.ingest.annotate import mentions

        for cid, corpus in self.corpora.items():
            for r in corpus.records:
                rid = f"{cid}/{r.record_id}"
                self._duplicates.setdefault((cid, r.duplicate_key), []).append(r.record_id)
                ms = mentions(r.problem_raw)
                self._source_mentions[rid] = ms
                comps = {m.value for m in ms if m.kind == "component"}
                comps.update(m.value.lower() for m in ms if m.kind == "component")
                comps.update(m.text.lower() for m in ms if m.kind == "component")
                for m in ms:
                    if m.kind == "cylinder_number":
                        comps.add("cylinder")
                        comps.add("cyl")
                    elif m.kind == "engine_number":
                        comps.add("engine")
                norm_tokens = set(r.problem_normalized.lower().split())
                if "cylinder" in norm_tokens:
                    comps.add("cylinder")
                if "cyl" in norm_tokens:
                    comps.add("cyl")
                if "engine" in norm_tokens:
                    comps.add("engine")
                self._source_components[rid] = comps
                symps = {m.value for m in ms if m.kind == "symptom"}
                symps.update(m.value.lower() for m in ms if m.kind == "symptom")
                symps.update(m.text.lower() for m in ms if m.kind == "symptom")
                self._source_symptoms[rid] = symps
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

        t_norm = time.perf_counter()
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
        norm_ms = (time.perf_counter() - t_norm) * 1000

        representation = "problem_action" if spec.intent == "action_history" else "problem"

        t_queue = time.perf_counter()
        async with self._cpu:
            queue_ms = (time.perf_counter() - t_queue) * 1000

            t_emb = time.perf_counter()
            query = None
            emb_cache_hit = False
            if "dense" in self.channels:
                q_cache_key = (spec.query_normalized, self.encoder.revision)
                if q_cache_key in self._query_cache:
                    query = self._query_cache[q_cache_key]
                    emb_cache_hit = True
                else:
                    query = await asyncio.to_thread(
                        self.encoder.encode_queries, [spec.query_normalized]
                    )
                    if len(self._query_cache) < 500:
                        self._query_cache[q_cache_key] = query
            embedding_ms = (time.perf_counter() - t_emb) * 1000

            result, metrics = await asyncio.to_thread(
                self._retrieve, spec, ids, representation, query
            )

            rerank_status = "skipped"
            rerank_pool_size = 0
            t_rerank = time.perf_counter()
            if spec.quality_mode:
                if self.reranker is None:
                    result.degraded_branches.append("reranker_unavailable")
                    rerank_status = "unavailable"
                elif self._reranker_busy:
                    result.degraded_branches.append("reranker_busy")
                    rerank_status = "busy"
                else:
                    pool = result.hits[:20]
                    rerank_pool_size = len(pool)
                    rows = {f"{r.corpus_id}/{r.record_id}": r for r in self.scoped_records(scope)}
                    pairs = [
                        (spec.query_raw, rows[f"{h.corpus_id}/{h.record_id}"].problem_raw)
                        for h in pool
                    ]
                    self._reranker_busy = True
                    loop = asyncio.get_running_loop()
                    fut = loop.run_in_executor(None, self.reranker.score, pairs)

                    def _done_cb(f):
                        self._reranker_busy = False
                        try:
                            f.exception()
                        except Exception:
                            pass

                    fut.add_done_callback(_done_cb)
                    try:
                        scores = await asyncio.wait_for(asyncio.shield(fut), timeout=1.5)
                        for h, score in zip(pool, scores, strict=True):
                            h.reranker_score = float(score)
                        order = {"direct": 0, "related": 1, "tangential": 2}
                        result.hits = sorted(
                            pool,
                            key=lambda h: (order[h.compatibility.tier], -h.reranker_score, h.record_id),
                        )
                        rerank_status = "executed"
                    except asyncio.TimeoutError:
                        result.degraded_branches.append("reranker_timeout")
                        rerank_status = "timeout"
                    except Exception:
                        result.degraded_branches.append("reranker_error")
                        rerank_status = "error"
            rerank_ms = (time.perf_counter() - t_rerank) * 1000

        t_topk = time.perf_counter()
        result.hits = result.hits[: spec.top_k]
        topk_ms = (time.perf_counter() - t_topk) * 1000

        total_ms = (time.perf_counter() - start) * 1000
        result.timings_ms = {
            "queue": queue_ms,
            "normalization": norm_ms,
            "embedding": embedding_ms,
            "compatibility_filtering": metrics["compat_ms"],
            "raw_bm25": metrics["raw_bm25_ms"],
            "normalized_bm25": metrics["norm_bm25_ms"],
            "dense_cosine": metrics["dense_ms"],
            "fusion": metrics["fusion_ms"],
            "dedup": metrics["dedup_ms"],
            "rerank": rerank_ms,
            "top_k_selection": topk_ms,
            "record_fetch": 0.0,
            "total": total_ms,
        }

        stages = [
            StageTrace(
                stage="queue",
                duration_ms=queue_ms,
                count_in=1,
                count_out=1,
                details={"status": "acquired"},
            ),
            StageTrace(
                stage="normalization",
                duration_ms=norm_ms,
                count_in=len(spec.query_raw),
                count_out=len(spec.query_normalized),
                details={"mentions_count": len(ms)},
            ),
            StageTrace(
                stage="embedding",
                duration_ms=embedding_ms,
                count_in=1 if "dense" in self.channels else 0,
                count_out=self.encoder.dimension if "dense" in self.channels else 0,
                details={
                    "channel": "dense",
                    "model": self.encoder.model_id,
                    "revision": self.encoder.revision,
                    "embedding_cache_hit": emb_cache_hit,
                    "embedding_cache_size": len(self._query_cache),
                },
            ),
            StageTrace(
                stage="compatibility_filtering",
                duration_ms=metrics["compat_ms"],
                count_in=metrics["total_scanned"],
                count_out=metrics["eligible_count"],
                details={
                    "filters": spec.filters.model_dump(),
                    "fused_pairs_assessed": metrics["fused_pairs_assessed"],
                    "total_scanned": metrics["total_scanned"],
                },
            ),
            StageTrace(
                stage="raw_bm25",
                duration_ms=metrics["raw_bm25_ms"],
                count_in=metrics["eligible_count"],
                count_out=metrics["raw_bm25_count"],
                details={"channel": "bm25_raw"},
            ),
            StageTrace(
                stage="normalized_bm25",
                duration_ms=metrics["norm_bm25_ms"],
                count_in=metrics["eligible_count"],
                count_out=metrics["norm_bm25_count"],
                details={"channel": "bm25_normalized"},
            ),
            StageTrace(
                stage="dense_cosine",
                duration_ms=metrics["dense_ms"],
                count_in=metrics["eligible_count"],
                count_out=metrics["dense_count"],
                details={"channel": "dense"},
            ),
            StageTrace(
                stage="fusion",
                duration_ms=metrics["fusion_ms"],
                count_in=metrics["raw_bm25_count"]
                + metrics["norm_bm25_count"]
                + metrics["dense_count"],
                count_out=metrics["fused_count"],
                details={"weights": WEIGHTS},
            ),
            StageTrace(
                stage="dedup",
                duration_ms=metrics["dedup_ms"],
                count_in=metrics["fused_count"],
                count_out=metrics["dedup_pool_count"],
                details={"collapse_duplicates": spec.collapse_duplicates},
            ),
            StageTrace(
                stage="rerank",
                duration_ms=rerank_ms,
                count_in=rerank_pool_size,
                count_out=rerank_pool_size,
                details={"quality_mode": spec.quality_mode, "status": rerank_status},
            ),
            StageTrace(
                stage="top_k_selection",
                duration_ms=topk_ms,
                count_in=min(20, metrics["dedup_pool_count"]),
                count_out=len(result.hits),
                details={"top_k": spec.top_k},
            ),
            StageTrace(
                stage="record_fetch",
                duration_ms=0.0,
                count_in=len(result.hits),
                count_out=len(result.hits),
                details={"status": "in_memory_snapshot_retained", "db_fetch": "not_executed_in_search"},
            ),
        ]
        result.trace = SearchTrace(
            stages=stages,
            stage_timings_ms={s.stage: s.duration_ms for s in stages},
            stage_counts={s.stage: s.count_out or 0 for s in stages},
            original_query=spec.query_raw,
            normalized_query=spec.query_normalized,
            query_mentions=ms,
        )
        return result

    def _retrieve(self, spec, ids, representation, query):
        channel_rows = {name: [] for name in self.channels}
        records = {}
        total_scanned = 0
        eligible_count = 0
        compat_ms = 0.0
        raw_bm25_ms = 0.0
        norm_bm25_ms = 0.0
        dense_ms = 0.0

        for cid in ids:
            key = cid if representation == "problem" else cid + ":problem_action"
            if key not in self.matrices:
                raise LookupError("requested representation not built")
            corpus = self.corpora[cid]
            total_scanned += len(corpus.records)
            raw, norm = self.indexes[key]

            t_compat = time.perf_counter()
            eligible = []
            comp_filter = spec.filters.component.strip().lower() if spec.filters.component else None
            symp_filter = spec.filters.symptom.strip().lower() if spec.filters.symptom else None
            for i, r in enumerate(corpus.records):
                rid = f"{cid}/{r.record_id}"
                if comp_filter and (comp_filter not in self._source_components[rid] and spec.filters.component not in self._source_components[rid]):
                    continue
                if symp_filter and (symp_filter not in self._source_symptoms[rid] and spec.filters.symptom not in self._source_symptoms[rid]):
                    continue
                eligible.append(i)
                records[rid] = r
            eligible_set = set(eligible)
            eligible_count += len(eligible)
            compat_ms += (time.perf_counter() - t_compat) * 1000

            paths = {}
            if "bm25_raw" in self.channels:
                t0 = time.perf_counter()
                paths["bm25_raw"] = raw.search(spec.query_raw, len(corpus.records))
                raw_bm25_ms += (time.perf_counter() - t0) * 1000
            if "bm25_normalized" in self.channels:
                t0 = time.perf_counter()
                paths["bm25_normalized"] = norm.search(spec.query_normalized, len(corpus.records))
                norm_bm25_ms += (time.perf_counter() - t0) * 1000
            if "dense" in self.channels and query is not None:
                t0 = time.perf_counter()
                paths["dense"] = exact_cosine(self.matrices[key], query[0], len(corpus.records))
                dense_ms += (time.perf_counter() - t0) * 1000

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

        t_fusion = time.perf_counter()
        fused = fuse_ranked_ids(channels, WEIGHTS)
        fusion_ms = (time.perf_counter() - t_fusion) * 1000

        t_post_compat = time.perf_counter()
        fused_comps = {}
        for h in fused:
            r = records[h["record_id"]]
            fused_comps[h["record_id"]] = assess(spec.query_raw, r.problem_raw)

        order = {"direct": 0, "related": 1, "tangential": 2}
        if self.use_compatibility:
            fused.sort(
                key=lambda h: (
                    order[fused_comps[h["record_id"]].tier],
                    -h["rrf_score"],
                    h["record_id"],
                )
            )
        compat_ms += (time.perf_counter() - t_post_compat) * 1000

        t_dedup = time.perf_counter()
        seen = set()
        hits = []
        for h in fused:
            r = records[h["record_id"]]
            comp = fused_comps[h["record_id"]]
            group = (str(r.corpus_id), r.duplicate_key)
            if spec.collapse_duplicates and group in seen:
                continue
            seen.add(group)
            members = sorted(self._duplicates.get(group, [r.record_id]))
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
                    record_snapshot=r.model_copy(deep=True),
                )
            )
        dedup_ms = (time.perf_counter() - t_dedup) * 1000

        public_channels = {
            name: [records[rid].record_id for rid in rids] for name, rids in channels.items()
        }
        metrics = {
            "total_scanned": total_scanned,
            "eligible_count": eligible_count,
            "compat_ms": compat_ms,
            "fused_pairs_assessed": len(fused_comps),
            "raw_bm25_ms": raw_bm25_ms,
            "raw_bm25_count": len(channel_rows.get("bm25_raw", [])),
            "norm_bm25_ms": norm_bm25_ms,
            "norm_bm25_count": len(channel_rows.get("bm25_normalized", [])),
            "dense_ms": dense_ms,
            "dense_count": len(channel_rows.get("dense", [])),
            "fusion_ms": fusion_ms,
            "fused_count": len(fused),
            "dedup_ms": dedup_ms,
            "dedup_pool_count": len(hits),
        }
        result = SearchResult(
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
        return result, metrics
