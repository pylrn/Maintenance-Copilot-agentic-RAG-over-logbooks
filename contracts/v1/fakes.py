"""Explicit synthetic services for P2 development. Never use as released evidence."""

import numpy as np

from maintenance.ingest.aviation import parse_aviation
from maintenance.retrieval.engine import RetrievalEngine


class FixtureEncoder:
    model_id = "fixture-only"
    revision = "fixture-only"
    query_prefix = ""
    dimension = 3

    def encode_queries(self, texts):
        return np.array([[1, 0, 0] for _ in texts], dtype=np.float32)


class FixtureSearchService(RetrievalEngine):
    def __init__(self):
        corpus = parse_aviation(
            b"IDENT,PROBLEM,ACTION\nDEMO-1,INTAKE LEAK,REPLACED GASKET\nDEMO-2,ROCKER COVER LEAK,REPLACED COVER\nDEMO-3,BATTERY FLAT,CHARGED\n"
        )
        super().__init__([corpus], {str(corpus.manifest.corpus_id): np.eye(3)}, FixtureEncoder())

    async def search(self, spec, scope):
        result = await super().search(spec, scope)
        result.fixture_only = True
        result.limitations.append("SYNTHETIC FIXTURE: not real maintenance evidence.")
        return result
