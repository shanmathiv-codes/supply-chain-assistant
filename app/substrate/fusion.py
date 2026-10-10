"""Reciprocal Rank Fusion (RRF) combining graph and semantic retrieval signals."""

from collections import defaultdict

from app.core.config import load_yaml_config
from app.schemas.report import CaseSignals

SYNAPT_CONFIG = load_yaml_config("synapt.yaml")
FUSION_CONFIG = SYNAPT_CONFIG.get("fusion", {})
K_DEFAULT = FUSION_CONFIG.get("reciprocal_rank_k", 60)
WEIGHTS_DEFAULT = FUSION_CONFIG.get(
    "weights",
    {
        "cypher_overlap": 0.35,
        "node_search": 0.25,
        "chunk_search": 0.25,
        "exact_lookup": 0.15,
    },
)


def fuse_signals(
    signal_rankings: dict[str, list[str]],
    weights: dict[str, float] | None = None,
    k: int = K_DEFAULT,
) -> list[tuple[str, float, CaseSignals]]:
    """Compute Reciprocal Rank Fusion over ranked lists of case IDs.
    Returns: list of (case_id, fused_score, CaseSignals) ordered by descending fused_score.
    """
    effective_weights = weights or WEIGHTS_DEFAULT
    scores: dict[str, float] = defaultdict(float)
    signals_by_case: dict[str, dict[str, float]] = defaultdict(dict)

    for signal_name, case_ids in signal_rankings.items():
        w = effective_weights.get(signal_name, 0.25)
        for rank_zero_based, cid in enumerate(case_ids):
            rank = rank_zero_based + 1
            rrf_component = w / (k + rank)
            scores[cid] += rrf_component
            signals_by_case[cid][signal_name] = round(rrf_component, 5)

    # Sort descending
    sorted_cases = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    result = []
    for cid, score in sorted_cases:
        sig_dict = signals_by_case[cid]
        cs = CaseSignals(
            cypher_overlap=sig_dict.get("cypher_overlap"),
            node_search=sig_dict.get("node_search"),
            chunk_search=sig_dict.get("chunk_search"),
            exact_lookup=sig_dict.get("exact_lookup"),
        )
        result.append((cid, round(score, 6), cs))

    return result
