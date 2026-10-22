import numpy as np


def normalized_matrix(vectors, dimension=None):
    matrix = np.asarray(vectors, dtype=np.float32)
    if (
        matrix.ndim != 2
        or not np.isfinite(matrix).all()
        or (dimension and matrix.shape[1] != dimension)
    ):
        raise ValueError("embedding shape or finite-value mismatch")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if (norms == 0).any():
        raise ValueError("zero embedding vector")
    return matrix / norms


def exact_cosine(matrix, query, limit=50):
    query = normalized_matrix(np.asarray(query).reshape(1, -1), matrix.shape[1])[0]
    scores = matrix @ query
    return [
        (int(i), float(scores[i]))
        for i in sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:limit]
    ]
