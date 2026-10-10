"""Retrieval evaluation metrics module.

Computes:
- Precision@K
- Recall@K
- Mean Reciprocal Rank (MRR)
- Normalized Discounted Cumulative Gain (nDCG@K)
- Attribute Agreement@K (proportion of top-K cases sharing query attributes)
"""

from __future__ import annotations

import math
from typing import Any


def precision_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int = 5) -> float:
    """Compute Precision@K."""
    if not retrieved_ids or k <= 0:
        return 0.0
    top_k = retrieved_ids[:k]
    hits = sum(1 for cid in top_k if cid in relevant_ids)
    return hits / min(len(top_k), k)


def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int = 5) -> float:
    """Compute Recall@K."""
    if not relevant_ids or not retrieved_ids or k <= 0:
        return 0.0
    top_k = retrieved_ids[:k]
    hits = sum(1 for cid in top_k if cid in relevant_ids)
    return hits / len(relevant_ids)


def reciprocal_rank(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    """Compute Reciprocal Rank of the first relevant hit."""
    for rank, cid in enumerate(retrieved_ids, 1):
        if cid in relevant_ids:
            return 1.0 / rank
    return 0.0


def dcg_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int = 5) -> float:
    """Compute Discounted Cumulative Gain at K (binary relevance)."""
    dcg = 0.0
    for rank, cid in enumerate(retrieved_ids[:k], 1):
        rel = 1.0 if cid in relevant_ids else 0.0
        dcg += rel / math.log2(rank + 1)
    return dcg


def ndcg_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int = 5) -> float:
    """Compute Normalized Discounted Cumulative Gain at K."""
    if not relevant_ids or not retrieved_ids or k <= 0:
        return 0.0
    actual_dcg = dcg_at_k(retrieved_ids, relevant_ids, k)

    # Ideal DCG with all relevant items placed first
    ideal_hits = min(len(relevant_ids), k)
    idcg = sum(1.0 / math.log2(r + 1) for r in range(1, ideal_hits + 1))
    if idcg <= 0.0:
        return 0.0
    return actual_dcg / idcg


def attribute_agreement_at_k(
    retrieved_cases: list[dict[str, Any]],
    query_profile: dict[str, Any],
    k: int = 5,
    key_attributes: list[str] | None = None,
) -> float:
    """Compute average fraction of key attributes matching the query in top-K cases."""
    if not retrieved_cases or k <= 0:
        return 0.0
    if key_attributes is None:
        key_attributes = ["disruption_type", "industry", "supplier_region"]

    top_k = retrieved_cases[:k]
    scores: list[float] = []

    for case in top_k:
        attrs = case.get("attributes", case)
        matches = 0
        valid_keys = 0
        for key in key_attributes:
            expected = query_profile.get(key)
            if expected is not None:
                valid_keys += 1
                if str(attrs.get(key, "")).lower() == str(expected).lower():
                    matches += 1
        scores.append(matches / valid_keys if valid_keys > 0 else 1.0)

    return sum(scores) / len(scores) if scores else 0.0


def evaluate_retrieval_batch(
    eval_queries: list[dict[str, Any]],
    search_func: Any,
    k_values: list[int] | None = None,
) -> dict[str, float]:
    """Evaluate retrieval performance across a batch of benchmark queries."""
    if k_values is None:
        k_values = [3, 5, 10]

    precisions: dict[int, list[float]] = {k: [] for k in k_values}
    recalls: dict[int, list[float]] = {k: [] for k in k_values}
    ndcgs: dict[int, list[float]] = {k: [] for k in k_values}
    rr_scores: list[float] = []
    attr_agreements: dict[int, list[float]] = {k: [] for k in k_values}

    for item in eval_queries:
        req = item["request"]
        relevant_ids = set(item.get("relevant_case_ids", []))
        if not relevant_ids:
            continue

        # Invoke search function
        results = search_func(req)
        retrieved_ids = [c.get("case_id", "") for c in results]

        for k in k_values:
            precisions[k].append(precision_at_k(retrieved_ids, relevant_ids, k))
            recalls[k].append(recall_at_k(retrieved_ids, relevant_ids, k))
            ndcgs[k].append(ndcg_at_k(retrieved_ids, relevant_ids, k))
            attr_agreements[k].append(attribute_agreement_at_k(results, req, k=k))

        rr_scores.append(reciprocal_rank(retrieved_ids, relevant_ids))

    n = max(len(rr_scores), 1)
    summary: dict[str, float] = {
        "mrr": sum(rr_scores) / n,
    }
    for k in k_values:
        summary[f"precision@{k}"] = (
            sum(precisions[k]) / len(precisions[k]) if precisions[k] else 0.0
        )
        summary[f"recall@{k}"] = sum(recalls[k]) / len(recalls[k]) if recalls[k] else 0.0
        summary[f"ndcg@{k}"] = sum(ndcgs[k]) / len(ndcgs[k]) if ndcgs[k] else 0.0
        summary[f"attribute_agreement@{k}"] = (
            sum(attr_agreements[k]) / len(attr_agreements[k]) if attr_agreements[k] else 0.0
        )

    return summary
