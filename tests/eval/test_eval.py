"""Tests for evaluation metrics, benchmark datasets, ablation, and judge suite."""

from __future__ import annotations

import json
from pathlib import Path

from evaluation.ablation import run_ablation_experiments
from evaluation.deepeval_suite import FakeJudgeModel, run_deepeval_benchmark
from evaluation.retrieval_metrics import (
    attribute_agreement_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


def test_retrieval_metrics_calculation():
    """Verify precision, recall, mrr, and ndcg calculation."""
    retrieved = ["DIS-1", "DIS-2", "DIS-3", "DIS-4", "DIS-5"]
    relevant = {"DIS-2", "DIS-5", "DIS-9"}

    prec3 = precision_at_k(retrieved, relevant, k=3)
    assert round(prec3, 3) == round(1 / 3, 3)  # DIS-2 only

    prec5 = precision_at_k(retrieved, relevant, k=5)
    assert prec5 == 2 / 5  # DIS-2, DIS-5

    rec5 = recall_at_k(retrieved, relevant, k=5)
    assert rec5 == 2 / 3  # 2 of 3 relevant found

    rr = reciprocal_rank(retrieved, relevant)
    assert rr == 0.5  # first hit at rank 2 (DIS-2)

    ndcg5 = ndcg_at_k(retrieved, relevant, k=5)
    assert 0.0 < ndcg5 <= 1.0


def test_attribute_agreement_calculation():
    """Verify attribute agreement@k across candidate cases."""
    query_profile = {
        "disruption_type": "Port Closure",
        "industry": "Automotive",
        "supplier_region": "APAC",
    }
    cases = [
        {
            "case_id": "DIS-1",
            "attributes": {
                "disruption_type": "Port Closure",
                "industry": "Automotive",
                "supplier_region": "APAC",
            },
        },
        {
            "case_id": "DIS-2",
            "attributes": {
                "disruption_type": "Port Closure",
                "industry": "Electronics",
                "supplier_region": "APAC",
            },
        },
    ]
    agreement = attribute_agreement_at_k(cases, query_profile, k=2)
    # Case 1: 3/3 = 1.0. Case 2: 2/3 = 0.6667. Mean = 0.8333
    assert 0.8 < agreement < 0.85


def test_evaluation_datasets_integrity():
    """Verify generated evaluation sets exist and adhere to contracts."""
    eval_dir = Path("dataset/evaluation")

    # Ingested IDs
    ingested_file = eval_dir / "ingested_ids.json"
    assert ingested_file.exists()
    with open(ingested_file, encoding="utf-8") as f:
        ingested_ids = set(json.load(f))
    assert len(ingested_ids) > 0

    # Retrieval Set: disjoint from ingested IDs
    ret_file = eval_dir / "retrieval_set.json"
    assert ret_file.exists()
    with open(ret_file, encoding="utf-8") as f:
        ret_queries = json.load(f)
    assert len(ret_queries) >= 30
    for q in ret_queries:
        assert q["disruption_id"] not in ingested_ids

    # QA Set
    qa_file = eval_dir / "qa_set.json"
    assert qa_file.exists()
    with open(qa_file, encoding="utf-8") as f:
        qa_data = json.load(f)
    assert len(qa_data) >= 30

    # Guardrails Set
    gr_file = eval_dir / "guardrails_set.json"
    assert gr_file.exists()
    with open(gr_file, encoding="utf-8") as f:
        gr_data = json.load(f)
    assert len(gr_data) >= 30


def test_ablation_experiments_runner(tmp_path):
    """Verify ablation experiments compute expected configs and output files."""
    results = run_ablation_experiments(n_samples=5)
    assert len(results) == 5

    config_names = [r["config_id"] for r in results]
    assert "Config A" in config_names
    assert "Config D" in config_names

    # Config D must have highest precision and 100% grounding
    cfg_d = next(r for r in results if r["config_id"] == "Config D")
    assert cfg_d["evidence_grounding_pct"] == 100.0
    assert cfg_d["hallucination_rate_pct"] == 0.0


def test_fake_judge_benchmark():
    """Verify offline judge scores test cases deterministically."""
    judge = FakeJudgeModel()
    scores = judge.evaluate_case(
        input_text="What response worked best for port closures?",
        actual_output="Based on EVD-001, expedited freight is associated with recovery in 14 days with uncertainty.",
        retrieval_context=[
            "EVD-001: Historical port closure cases in APAC show expedited freight."
        ],
    )

    assert "faithfulness" in scores
    assert "answer_relevancy" in scores
    assert "evidence_alignment" in scores
    assert "uncertainty_disclosure" in scores
    assert scores["evidence_alignment"] >= 0.90
    assert scores["uncertainty_disclosure"] == 1.0


def test_deepeval_benchmark_runner():
    """Verify DeepEval benchmark runner runs with budget=small."""
    res = run_deepeval_benchmark(budget="small", use_fake_judge=True)
    assert res["budget"] == "small"
    assert res["n_evaluated"] > 0
    assert "faithfulness" in res["metrics_summary"]
