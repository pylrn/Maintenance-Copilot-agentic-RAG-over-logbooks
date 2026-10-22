import numpy as np
import pytest

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
