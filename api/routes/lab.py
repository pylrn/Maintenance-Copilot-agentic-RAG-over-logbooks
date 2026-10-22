"""Lab inspection endpoints for retrieval workbench: records, storage, projection.

Bounded, authenticated, read-only inspection over real engine matrices and corpora.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from maintenance.auth import require_owner
from maintenance.contracts import Domain
from maintenance.ingest.annotate import mentions

router = APIRouter()


def compute_deterministic_pca2(
    matrix: np.ndarray,
) -> tuple[np.ndarray, list[float], float]:
    """Compute 2D centered PCA using deterministic numpy SVD with sign orientation.

    Returns:
        projected: (N, 2) array of coordinates
        explained_variance_ratio: [float, float]
        total_explained_variance: float
    """
    n_samples, n_features = matrix.shape
    if n_samples < 2 or n_features < 2:
        projected = np.zeros((n_samples, 2), dtype=np.float32)
        return projected, [0.0, 0.0], 0.0

    # 1. Center the data
    mean = np.mean(matrix, axis=0)
    centered = matrix - mean

    # 2. SVD: centered = U * S * Vt
    # Vt has shape (min(n_samples, n_features), n_features)
    # Right singular vectors (rows of Vt) are the principal directions
    _, s, vt = np.linalg.svd(centered, full_matrices=False)

    components = vt[:2]  # (2, n_features)

    # 3. Deterministic sign flip: ensure max absolute value in each principal direction is positive
    for i in range(min(2, len(components))):
        max_idx = int(np.argmax(np.abs(components[i])))
        if components[i, max_idx] < 0:
            components[i] *= -1.0

    # 4. Project data
    projected = np.dot(centered, components.T)  # (n_samples, 2)

    # 5. Explained variance calculation
    variances = (s**2) / (n_samples - 1)
    total_var = float(np.sum(variances))
    if total_var > 0:
        evr = [float(variances[0] / total_var), float(variances[1] / total_var)]
    else:
        evr = [0.0, 0.0]

    return projected, evr, float(sum(evr))


@router.get("/records")
async def get_lab_records(
    request: Request,
    domain: Domain | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    search: str | None = None,
    corpus_id: UUID | None = None,
    component: str | None = None,
    symptom: str | None = None,
    owner: UUID = Depends(require_owner),
):
    """Bounded, paginated inspection of corpus records with real source fields and hashes."""
    engine = request.app.state.search_engine
    if engine is None:
        raise HTTPException(503, "retrieval_unavailable")

    if corpus_id is not None and str(corpus_id) not in engine.corpora:
        raise HTTPException(404, "corpus_not_found")

    # Collect records from scoped corpora
    all_records = []
    for cid_str, corpus in engine.corpora.items():
        if corpus_id is not None and str(corpus.manifest.corpus_id) != str(corpus_id):
            continue
        if domain is not None and corpus.manifest.domain != domain:
            continue
        all_records.extend(corpus.records)

    # Apply filters
    filtered = []
    search_lower = search.strip().lower() if search and search.strip() else None
    comp_lower = component.strip().lower() if component and component.strip() else None
    symp_lower = symptom.strip().lower() if symptom and symptom.strip() else None

    for r in all_records:
        if search_lower:
            haystack = f"{r.record_id} {r.source_id} {r.problem_raw} {r.action_raw or ''}".lower()
            if search_lower not in haystack:
                continue
        if comp_lower or symp_lower:
            ms = mentions(r.problem_raw)
            comps = {m.value.lower() for m in ms if m.kind == "component"} | {
                m.text.lower() for m in ms if m.kind == "component"
            }
            # Documented relations: cylinder_number implies cylinder component, engine_number implies engine
            for m in ms:
                if m.kind == "cylinder_number":
                    comps.add("cylinder")
                    comps.add("cyl")
                elif m.kind == "engine_number":
                    comps.add("engine")
            norm_tokens = set(r.problem_normalized.lower().split())
            comps.update(norm_tokens)

            symps = {m.value.lower() for m in ms if m.kind == "symptom"} | {
                m.text.lower() for m in ms if m.kind == "symptom"
            }
            symps.update(norm_tokens)

            if comp_lower and comp_lower not in comps and comp_lower not in r.problem_raw.lower():
                continue
            if symp_lower and symp_lower not in symps and symp_lower not in r.problem_raw.lower():
                continue
        filtered.append(r)

    total = len(filtered)
    total_pages = max(1, (total + page_size - 1) // page_size)
    offset = (page - 1) * page_size
    sliced = filtered[offset : offset + page_size]

    items = [
        {
            "record_id": r.record_id,
            "source_id": r.source_id,
            "domain": r.domain,
            "corpus_id": str(r.corpus_id),
            "csv_row": r.csv_row,
            "problem_raw": r.problem_raw,
            "action_raw": r.action_raw,  # null for facility
            "problem_normalized": r.problem_normalized,
            "action_normalized": r.action_normalized,  # null for facility
            "original_fields": r.original_fields,
            "field_sha256": r.field_sha256,
            "source_file_sha256": r.source_file_sha256,
            "duplicate_key": r.duplicate_key,
            "source_model": r.source_model,
        }
        for r in sliced
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/storage")
async def get_lab_storage(
    request: Request,
    owner: UUID = Depends(require_owner),
):
    """Dynamic database and table sizes, record/vector counts, index counts, and quota status.

    Returns real database metrics when connected, or database_status='unavailable' with null bytes.
    Index counts and index memory are always reported truthfully from engine without substitution.
    """
    engine = request.app.state.search_engine
    if engine is None:
        raise HTTPException(503, "retrieval_unavailable")

    now_iso = datetime.now(timezone.utc).isoformat()
    quota_bytes = 500_000_000  # 500 MB quota labelled Free plan database quota (configured 500MB)
    quota_label = "Free plan database quota (configured 500MB)"

    db = request.app.state.db
    tables = {}
    db_index_count = None
    db_records = None
    db_vectors = None
    db_bytes = None
    db_status = "unavailable"

    if db is not None and db.pool is not None:
        try:
            async with db.pool.acquire() as conn:
                db_name = await conn.fetchval("SELECT current_database()")
                db_bytes = int(await conn.fetchval("SELECT pg_database_size($1)", db_name) or 0)
                db_status = "connected"

                # Table sizes & row counts
                for tbl in ["maintenance_records", "record_embeddings", "corpus_versions"]:
                    try:
                        tbl_bytes = int(
                            await conn.fetchval("SELECT pg_total_relation_size($1)", tbl) or 0
                        )
                        tbl_rows = int(await conn.fetchval(f"SELECT count(*) FROM {tbl}") or 0)
                        tables[tbl] = {"bytes": tbl_bytes, "row_count": tbl_rows}
                    except Exception:
                        pass

                db_records = tables.get("maintenance_records", {}).get("row_count")
                db_vectors = tables.get("record_embeddings", {}).get("row_count")

                # Indexes count
                db_index_count = int(
                    await conn.fetchval(
                        "SELECT count(*) FROM pg_indexes WHERE schemaname = ANY(current_schemas(true))"
                    )
                    or 0
                )
        except Exception:
            db_bytes = None
            db_status = "error"

    # Engine in-memory dense vector truth
    dense_vector_memory_bytes = sum(m.nbytes for m in engine.matrices.values())
    index_record_count = sum(len(c.records) for c in engine.corpora.values())
    index_vector_count = sum(len(m) for m in engine.matrices.values())

    domain_counts = {}
    for c in engine.corpora.values():
        domain_counts[c.manifest.domain] = domain_counts.get(c.manifest.domain, 0) + len(c.records)

    index_counts = {
        "bm25_indexes": len(engine.indexes) * 2,
        "dense_matrices": len(engine.matrices),
    }
    if db_index_count is not None:
        index_counts["database_indexes"] = db_index_count

    free_bytes = max(0, quota_bytes - db_bytes) if db_bytes is not None else None

    return {
        "timestamp": now_iso,
        "quota_bytes": quota_bytes,
        "quota_label": quota_label,
        "database_status": db_status,
        "database_bytes": db_bytes,
        "free_bytes": free_bytes,
        "tables": tables,
        "db_records": db_records,
        "db_vectors": db_vectors,
        "dense_vector_memory_bytes": dense_vector_memory_bytes,
        "index_record_count": index_record_count,
        "index_vector_count": index_vector_count,
        "index_counts": index_counts,
        "domains": domain_counts,
        "source_labels": {
            "database": "Connected PostgreSQL / pgvector",
            "retrieval_index": "In-memory normalized dense matrices + BM25",
        },
    }


@router.get("/projection")
async def get_lab_projection(
    request: Request,
    representation: Literal["problem", "problem_action"] = "problem",
    corpus_id: UUID | None = None,
    max_points: int = Query(default=10000, ge=1, le=10000),
    owner: UUID = Depends(require_owner),
):
    """Deterministic centered 2D PCA projection over REAL engine matrices.

    Plot all records without corpus sampling, bounded to max 10000 points.
    Cached per immutable engine instance (maximum 6 entries for 2 corpora), slicing max_points on response.
    """
    engine = request.app.state.search_engine
    if engine is None:
        raise HTTPException(503, "retrieval_unavailable")

    if corpus_id is not None and str(corpus_id) not in engine.corpora:
        raise HTTPException(404, "corpus_not_found")

    corpus_filter = str(corpus_id) if corpus_id else None
    cache_key = (representation, corpus_filter)

    async with engine._projection_lock:
        if cache_key in engine._projection_cache:
            base_payload = engine._projection_cache[cache_key]
        else:
            # Gather target corpora
            target_cids = []
            for cid_str, c in engine.corpora.items():
                if corpus_filter and cid_str != corpus_filter:
                    continue
                target_cids.append(cid_str)

            if not target_cids:
                raise HTTPException(404, "no_matching_corpora")

            # Assemble matrix and aligned record metadata from real engine.matrices
            matrix_chunks = []
            point_metadata = []
            source_hash_builder = hashlib.sha256()

            for cid in sorted(target_cids):
                key = cid if representation == "problem" else f"{cid}:problem_action"
                if key not in engine.matrices:
                    raise HTTPException(404, f"matrix_representation_missing:{key}")

                mat = engine.matrices[key]
                corpus = engine.corpora[cid]
                matrix_chunks.append(mat)
                source_hash_builder.update(corpus.manifest.sha256.encode("utf-8"))

                for r in corpus.records:
                    point_metadata.append(
                        {
                            "record_id": r.record_id,
                            "source_id": r.source_id,
                            "corpus_id": str(r.corpus_id),
                            "domain": r.domain,
                            "problem_raw": (
                                r.problem_raw[:140] + "..."
                                if len(r.problem_raw) > 140
                                else r.problem_raw
                            ),
                            "action_raw": r.action_raw,  # null for facility
                            "duplicate_key": r.duplicate_key,
                        }
                    )

            if not matrix_chunks:
                raise HTTPException(404, "no_vectors_available")

            combined_matrix = np.vstack(matrix_chunks)

            # Run deterministic centered PCA in worker thread
            projected, evr, total_ev = await asyncio.to_thread(
                compute_deterministic_pca2, combined_matrix
            )

            all_points = []
            for meta, coords in zip(point_metadata, projected, strict=True):
                all_points.append(
                    {
                        "record_id": meta["record_id"],
                        "source_id": meta["source_id"],
                        "corpus_id": meta["corpus_id"],
                        "domain": meta["domain"],
                        "x": round(float(coords[0]), 4),
                        "y": round(float(coords[1]), 4),
                        "problem_raw": meta["problem_raw"],
                        "action_raw": meta["action_raw"],
                        "duplicate_key": meta["duplicate_key"],
                    }
                )

            base_payload = {
                "method": "deterministic_centered_pca2_svd",
                "representation": representation,
                "explained_variance": [round(x, 6) for x in evr],
                "total_explained_variance": round(total_ev, 6),
                "model_id": engine.encoder.model_id,
                "model_revision": engine.encoder.revision,
                "source_hash": source_hash_builder.hexdigest(),
                "all_points": all_points,
                "label": "inspection_only_not_retrieval_score",
            }
            engine._projection_cache[cache_key] = base_payload

    # Slice max_points on response without mutating cached full projection
    points = base_payload["all_points"][:max_points]
    return {
        "method": base_payload["method"],
        "representation": base_payload["representation"],
        "explained_variance": base_payload["explained_variance"],
        "total_explained_variance": base_payload["total_explained_variance"],
        "model_id": base_payload["model_id"],
        "model_revision": base_payload["model_revision"],
        "source_hash": base_payload["source_hash"],
        "total_points": len(points),
        "corpus_total": len(base_payload["all_points"]),
        "label": base_payload["label"],
        "points": points,
    }
