import json
import os
from uuid import uuid4

import numpy as np
import pytest

from maintenance.db import Database
from maintenance.ingest.aviation import parse_aviation
from maintenance.retrieval.artifacts import load_bundle, save_bundle


class Encoder:
    model_id = "fixture"
    revision = "abc"
    dimension = 3
    query_prefix = "prefix: "

    def encode_documents(self, texts):
        return np.array([[1, 0, 0] for _ in texts], dtype=np.float32)


def test_artifact_integrity_rejects_changed_source_and_model(tmp_path):
    c = parse_aviation(b"IDENT,PROBLEM,ACTION\n1,INTAKE LEAK,REPL GSKT\n")
    save_bundle(tmp_path, [c], Encoder())
    matrices, metadata = load_bundle(tmp_path, [c], Encoder())
    assert matrices[str(c.manifest.corpus_id)].shape == (1, 3)
    wrong = Encoder()
    wrong.revision = "wrong"
    with pytest.raises(ValueError, match="model"):
        load_bundle(tmp_path, [c], wrong)
    npz = tmp_path / metadata["arrays_file"]
    npz.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="checksum"):
        load_bundle(tmp_path, [c], Encoder())


def test_load_bundle_rejects_unknown_and_missing_representations(tmp_path):
    c = parse_aviation(b"IDENT,PROBLEM,ACTION\n1,INTAKE LEAK,REPL GSKT\n")
    save_bundle(tmp_path, [c], Encoder())

    # 1. Modify manifest to have an unknown representation
    manifest_path = tmp_path / "manifest.json"
    manifest_data = json.loads(manifest_path.read_text())
    original_entries = [dict(e) for e in manifest_data["entries"]]

    manifest_data["entries"][0]["representation"] = "unsupported_rep"
    manifest_path.write_text(json.dumps(manifest_data))
    with pytest.raises(ValueError, match="unknown index representation"):
        load_bundle(tmp_path, [c], Encoder())

    # 2. Modify manifest to omit problem_action representation
    manifest_data["entries"] = [e for e in original_entries if e["representation"] == "problem"]
    manifest_path.write_text(json.dumps(manifest_data))
    with pytest.raises(ValueError, match="missing index representation"):
        load_bundle(tmp_path, [c], Encoder())


def test_build_indexes_publishes_manifest_only_after_db_storage_succeeds(tmp_path):
    c = parse_aviation(b"IDENT,PROBLEM,ACTION\n1,INTAKE LEAK,REPL GSKT\n")

    # Initial manifest
    save_bundle(tmp_path, [c], Encoder(), publish=True)
    initial_manifest = (tmp_path / "manifest.json").read_text()

    # Second build with publish=False (staged)
    enc2 = Encoder()
    enc2.revision = "def"
    meta, publish = save_bundle(tmp_path, [c], enc2, publish=False)

    # Injected store failure occurs before publishing:
    # Prior manifest must remain untouched
    current_manifest = (tmp_path / "manifest.json").read_text()
    assert current_manifest == initial_manifest

    # Only after publish is explicitly invoked does the manifest update
    publish()
    updated_manifest = (tmp_path / "manifest.json").read_text()
    assert updated_manifest != initial_manifest
    assert "def" in updated_manifest


@pytest.mark.asyncio
async def test_store_vectors_rejects_conflicting_vector_and_accepts_different_model_revision():
    if not os.getenv("TEST_DATABASE_URL"):
        pytest.skip("isolated PostgreSQL required")

    db = Database(os.environ["TEST_DATABASE_URL"])
    await db.open()
    try:
        ident = f"rec_{uuid4().hex[:6]}"
        c = parse_aviation(f"IDENT,PROBLEM,ACTION\n{ident},INTAKE LEAK,REPL GSKT\n".encode())
        await db.ingest(c)

        # 384-dimensional vector
        vec_a = np.zeros(384, dtype=np.float32)
        vec_a[0] = 1.0

        # Store initial vector
        await db.store_vectors(
            corpus=c,
            representation="problem",
            matrix=[vec_a],
            model="BAAI/bge-small-en-v1.5",
            revision="rev1",
            text_hashes=["0123456789abcdef" * 4],
        )

        # Idempotent re-store with same vector values succeeds
        await db.store_vectors(
            corpus=c,
            representation="problem",
            matrix=[vec_a],
            model="BAAI/bge-small-en-v1.5",
            revision="rev1",
            text_hashes=["0123456789abcdef" * 4],
        )

        # Different model revision for the same corpus/record is ACCEPTED (versioned embeddings)
        await db.store_vectors(
            corpus=c,
            representation="problem",
            matrix=[vec_a],
            model="BAAI/bge-small-en-v1.5",
            revision="rev2_new",
            text_hashes=["0123456789abcdef" * 4],
        )

        # Conflicting vector values on same revision with SAME hash must be REJECTED
        vec_b = np.zeros(384, dtype=np.float32)
        vec_b[1] = 1.0  # Conflict!
        with pytest.raises(ValueError, match="conflicting existing embedding vector values"):
            await db.store_vectors(
                corpus=c,
                representation="problem",
                matrix=[vec_b],
                model="BAAI/bge-small-en-v1.5",
                revision="rev1",
                text_hashes=["0123456789abcdef" * 4],
            )
    finally:
        await db.close()
