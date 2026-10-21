"""Pinned local encoder; never imported or downloaded at module import time."""

import re


class BGEEncoder:
    model_id = "BAAI/bge-small-en-v1.5"
    dimension = 384

    def __init__(
        self,
        revision,
        cache_dir="models",
        query_prefix="Represent this sentence for searching relevant passages: ",
        local_only=True,
    ):
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ValueError("embedding revision must be an immutable 40-character model commit")
        from sentence_transformers import SentenceTransformer

        self.revision = revision
        self.query_prefix = query_prefix
        self.model = SentenceTransformer(
            self.model_id,
            revision=revision,
            cache_folder=str(cache_dir),
            local_files_only=local_only,
            device="cpu",
            trust_remote_code=False,
        )
        if self.model.get_embedding_dimension() != 384:
            raise ValueError("embedding dimension mismatch")

    def encode_documents(self, texts):
        return self.model.encode(
            texts,
            batch_size=64,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

    def encode_queries(self, texts):
        return self.model.encode(
            [self.query_prefix + t for t in texts],
            batch_size=16,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
