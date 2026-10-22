from uuid import uuid4

import numpy as np
import pytest

from maintenance.contracts import SearchSpec, ServiceScope
from maintenance.features.patterns import PatternService
from maintenance.features.sensitivity import SensitivityService
from maintenance.ingest.aviation import parse_aviation
from maintenance.retrieval.bm25 import BM25Index
from maintenance.retrieval.engine import RetrievalEngine
from maintenance.retrieval.fusion import fuse_ranked_ids


def test_rrf_is_deterministic_and_does_not_double_count_channel_ids():
    result = fuse_ranked_ids({"raw": ["a", "a", "b"], "dense": ["b"]}, {"raw": 0.5, "dense": 1})
    assert result[0]["record_id"] == "b"
    assert result[1]["rrf_score"] == pytest.approx(0.5 / 61)


def test_no_lexical_hits_when_all_scores_are_zero():
    idx = BM25Index(["leak intake", "cover crack", "battery flat"])
    assert idx.search("unicorn") == []


class Encoder:
    model_id = "fixture-encoder"
    revision = "fixture-only"
    dimension = 3
    query_prefix = ""

    def encode_queries(self, texts):
        return np.array([[1, 0, 0] for _ in texts], dtype=np.float32)


def setup_engine():
    corpus = parse_aviation(
        b"IDENT,PROBLEM,ACTION\n1,CYL #2 INTAKE LEAK,REPL GSKT\n2,CYL #2 INTAKE LEAK,REPL GSKT\n3,CYL #4 INTAKE LEAK,REPL TUBE\n4,BATTERY FLAT,CHARGED\n5,ROCKER COVER LEAK,REPL GSKT\n"
    )
    scope = ServiceScope(owner_id=uuid4(), corpus_ids=[corpus.manifest.corpus_id])
    vectors = np.array([[1, 0, 0], [1, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float32)
    return (
        RetrievalEngine([corpus], {str(corpus.manifest.corpus_id): vectors}, Encoder()),
        corpus,
        scope,
    )


async def test_real_channels_duplicates_conflicts_and_source_scope():
    engine, corpus, scope = setup_engine()
    result = await engine.search(
        SearchSpec(
            query_raw="CYL #2 intake leaking", domain="aviation", corpus_ids=scope.corpus_ids
        ),
        scope,
    )
    assert set(result.channels) == {"bm25_raw", "bm25_normalized", "dense"}
    assert result.hits[0].record_id == "aviation:1"
    assert result.hits[0].duplicate_ids == ["aviation:1", "aviation:2"]
    hit3 = next(h for h in result.hits if h.record_id == "aviation:3")
    assert hit3.compatibility.tier == "related"
    records = await engine.fetch(["aviation:1"], scope)
    assert records[0].action_raw == "REPL GSKT"
    with pytest.raises(PermissionError):
        await engine.search(
            SearchSpec(query_raw="leak", domain="aviation", corpus_ids=[uuid4()]), scope
        )
    with pytest.raises(LookupError):
        await engine.fetch(["facility:1"], scope)


async def test_patterns_keep_raw_and_distinct_counts_with_stable_receipt():
    engine, corpus, scope = setup_engine()
    service = PatternService(engine)
    result = await service.summarize({"component": "intake"}, scope)
    assert result.result["raw_rows"] == 3
    assert result.result["distinct_pairs"] == 2
    assert (
        result.manifest_sha256
        == (await service.summarize({"component": "intake"}, scope)).manifest_sha256
    )


async def test_sensitivity_requires_single_disclosed_change():
    engine, _, scope = setup_engine()
    service = SensitivityService(engine)
    base = SearchSpec(
        query_raw="CYL #2 intake leak", domain="aviation", corpus_ids=scope.corpus_ids
    )
    with pytest.raises(ValueError):
        await service.compare_specs(base, [base.model_copy(update={"domain": "facility"})], scope)


def test_negation_and_explicit_engine_cylinder_disagreement_not_direct():
    from maintenance.retrieval.compatibility import assess

    assert assess("intake leaking", "NO INTAKE LEAK").tier != "direct"
    assert assess("intake leak engine #2", "intake leak cylinder #2").tier != "direct"


async def test_sensitivity_receipt_has_original_and_rank_deltas():
    engine, _, scope = setup_engine()
    base = SearchSpec(
        query_raw="CYL #2 intake leak", domain="aviation", corpus_ids=scope.corpus_ids
    )
    changed = base.model_copy(update={"query_raw": "intake leak"})
    receipt = await SensitivityService(engine).compare_specs(base, [changed], scope)
    assert receipt.result["comparisons"][0]["change"] == "number_removed"
    assert receipt.result["base_top5"]
    assert receipt.result["comparisons"][0]["overlap"] >= 0
