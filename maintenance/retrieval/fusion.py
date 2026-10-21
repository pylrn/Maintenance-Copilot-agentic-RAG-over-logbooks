"""Adapted from Talent rank fusion; maintenance record keys and explicit channel weights."""

from collections import defaultdict


def fuse_ranked_ids(channels, weights, rank_constant=60):
    if rank_constant < 1:
        raise ValueError("rank constant must be positive")
    scores = defaultdict(float)
    ranks = defaultdict(dict)
    for name, ids in channels.items():
        seen = set()
        for rank, rid in enumerate(ids, 1):
            if rid in seen:
                continue
            seen.add(rid)
            ranks[rid][name] = rank
            scores[rid] += weights[name] / (rank_constant + rank)
    return [
        {"record_id": rid, "rrf_score": scores[rid], "channel_ranks": ranks[rid]}
        for rid in sorted(scores, key=lambda r: (-scores[r], r))
    ]
