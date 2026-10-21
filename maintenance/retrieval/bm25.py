import numpy as np
from rank_bm25 import BM25Okapi

from maintenance.ingest.normalize import tokenize


class BM25Index:
    def __init__(self, texts):
        self.tokens = [tokenize(t) for t in texts]
        if not self.tokens or not any(self.tokens):
            raise ValueError("empty lexical index")
        self.index = BM25Okapi(self.tokens)

    def search(self, query, limit=50):
        scores = self.index.get_scores(tokenize(query))
        return [
            (int(i), float(scores[i]))
            for i in sorted(np.flatnonzero(scores > 0), key=lambda i: (-scores[i], i))[:limit]
        ]
