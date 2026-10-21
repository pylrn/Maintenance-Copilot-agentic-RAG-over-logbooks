"""Atomic manifest+NPZ index artifacts; no pickle or source data redistribution."""

import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4

import numpy as np

from maintenance.ingest.manifest import sha256
from maintenance.retrieval.dense import normalized_matrix


def documents(corpus, representation):
    return [
        r.problem_normalized
        + ("\n" + (r.action_normalized or "") if representation == "problem_action" else "")
        for r in corpus.records
    ]


def model_metadata(encoder):
    return {
        "model_id": encoder.model_id,
        "revision": encoder.revision,
        "dimension": encoder.dimension,
        "query_prefix": encoder.query_prefix,
        "normalized": True,
    }


def save_bundle(directory, corpora, encoder):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    arrays = {}
    entries = []
    for c in corpora:
        for representation in ["problem", "problem_action"]:
            key = f"array_{len(entries)}"
            texts = documents(c, representation)
            matrix = normalized_matrix(encoder.encode_documents(texts), encoder.dimension)
            if len(matrix) != len(c.records):
                raise ValueError("encoded row mismatch")
            arrays[key] = matrix
            entries.append(
                {
                    "array_key": key,
                    "corpus_id": str(c.manifest.corpus_id),
                    "source_sha256": c.manifest.sha256,
                    "normalizer": c.manifest.normalization_version,
                    "representation": representation,
                    "record_ids": [r.record_id for r in c.records],
                    "document_hashes": [sha256(t) for t in texts],
                }
            )
    token = uuid4().hex
    arrays_name = f"vectors-{token}.npz"
    temp = directory / f".{arrays_name}"
    with temp.open("wb") as stream:
        np.savez_compressed(stream, **arrays)
    os.replace(temp, directory / arrays_name)
    metadata = {
        "index_version": "index/v1",
        "model": model_metadata(encoder),
        "entries": entries,
        "arrays_file": arrays_name,
        "arrays_sha256": hashlib.sha256((directory / arrays_name).read_bytes()).hexdigest(),
    }
    tmp = directory / f".manifest-{token}.json"
    tmp.write_text(json.dumps(metadata, sort_keys=True, indent=2))
    os.replace(tmp, directory / "manifest.json")
    return metadata


def load_bundle(directory, corpora, encoder):
    directory = Path(directory)
    meta = json.loads((directory / "manifest.json").read_text())
    if meta["index_version"] != "index/v1" or meta["model"] != model_metadata(encoder):
        raise ValueError("index model configuration mismatch")
    name = meta["arrays_file"]
    if Path(name).name != name:
        raise ValueError("invalid array filename")
    blob = (directory / name).read_bytes()
    if hashlib.sha256(blob).hexdigest() != meta["arrays_sha256"]:
        raise ValueError("array checksum mismatch")
    source = {str(c.manifest.corpus_id): c for c in corpora}
    matrices = {}
    with np.load(directory / name, allow_pickle=False) as archive:
        for e in meta["entries"]:
            c = source.get(e["corpus_id"])
            if (
                c is None
                or e["source_sha256"] != c.manifest.sha256
                or e["normalizer"] != c.manifest.normalization_version
            ):
                raise ValueError("index source version mismatch")
            if e["record_ids"] != [r.record_id for r in c.records] or e["document_hashes"] != [
                sha256(t) for t in documents(c, e["representation"])
            ]:
                raise ValueError("index source text/order mismatch")
            matrix = normalized_matrix(archive[e["array_key"]], encoder.dimension)
            if len(matrix) != len(c.records):
                raise ValueError("index shape mismatch")
            key = e["corpus_id"] + (
                ":problem_action" if e["representation"] == "problem_action" else ""
            )
            if key in matrices:
                raise ValueError("duplicate index representation")
            matrices[key] = matrix
    if set(source) != {e["corpus_id"] for e in meta["entries"]}:
        raise ValueError("missing indexed corpus")
    return matrices, meta
