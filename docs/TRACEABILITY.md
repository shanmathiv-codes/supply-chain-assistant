# Requirements Traceability Matrix

> **Scope:** Full mapping from specification requirements to Synapt tools, source files, automated test cases, and empirical proof artifacts.

---

| Spec Section | Requirement Description | Substrate Tool / Mechanism | Primary Implementation File | Automated Test File | Verification Proof Artifact | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **8.1 - 8.4** | Clean raw 100k CSV, validate schemas, store SQLite & Parquet | Data Pipeline / Pandas | `data_preprocessing/data_cleaning/cleaners.py`, `sqlite_io.py`, `parquet_io.py` | `tests/data/test_data_pipeline.py` | `dataset/processed/cases_clean.parquet`, `dataset/store/disruptions.db` | PASS |
| **8.5** | Stratified 80/10/10 disjoint splits & 500-case Synapt sample | Stratified Sampling | `data_preprocessing/preprocessing/splitting.py`, `synapt_sample.py` | `tests/data/test_data_pipeline.py` | `dataset/splits/train.parquet`, `dataset/synapt_sample/sample_ids.json` | PASS |
| **8.6 - 8.7** | Markdown case cards & derived SOP playbooks | Deterministic Generators | `data_preprocessing/case_cards/playbooks.py`, `cards/` | `tests/data/test_data_pipeline.py` | `dataset/playbooks/*.md`, `dataset/case_cards/_index.json` | PASS |
| **9.1 - 9.3** | 17 Synapt MCP tools, Gateway interfaces, Dynamic Adapters | MCP / Replay / Mock | `app/substrate/gateway.py`, `mock_adapter.py`, `replay_adapter.py` | `tests/contract/test_gateways.py` | `tests/contract/test_gateways.py::test_mock_adapter_implements_read_tools` | PASS |
| **9.2** | Permission boundary ban (app cannot import AdminGateway) | Python AST / Symbol Check | `app/substrate/permissions.py` | `tests/unit/test_permissions.py` | `test_admin_gateway_import_ban` | PASS |
| **9.5** | Parameterized Cypher templates with `exclude_case_ids` | Read Cypher Engine | `app/substrate/templates.py`, `cypher_templates/*.cypher` | `tests/contract/test_gateways.py` | `test_cypher_template_rendering` | PASS |
| **9.6** | 4-Signal Hybrid Retrieval with RRF and Relaxation Ladder | `trident_cypher`, `trident_search`, `trident_get_chunks`, `trident_find_exact` | `app/services/retrieval.py`, `app/substrate/fusion.py` | `tests/api/test_api.py`, `tests/eval/test_eval.py` | `artifacts/reports/ablation_results.csv`, `test_search_endpoint` | PASS |
| **10.1** | LiteLLM Router, Offline Safety Flags, SQLite SHA256 Cache | Router & Token Bucket | `app/llm/router.py`, `cache.py`, `fake.py` | `tests/unit/test_llm.py` | `dataset/store/llm_cache.db`, `test_fake_llm_all_prompts` | PASS |
| **11.1 - 11.4** | ML Regressors & 80% Split-Conformal Prediction Intervals | Conformal Residual Quantiles | `ml/training/train_regressors.py`, `conformal.py` | `tests/ml/test_ml.py` | `artifacts/models/*/model_card.json` (Coverage: 79.7% - 80.0%) | PASS |
| **11.6** | Predictive Feature Explainability (TreeExplainer & Permutation) | SHAP / Permutation Fallback | `ml/explain/shap_explain.py`, `permutation.py` | `tests/ml/test_ml.py` | `test_model_registry_and_shap_explain` | PASS |
| **11.7 - 11.8** | Resilience Score & Formula Prioritization (P1-P4 + Sensitivity) | Deterministic Formulas | `app/services/prioritization.py`, `ml/resilience.py` | `tests/api/test_api.py`, `tests/ml/test_ml.py` | `test_prioritize_endpoint`, `test_resilience_calculator` | PASS |
| **12.1 - 12.3** | LangGraph Multi-Agent StateGraph with 9 Nodes & Repair Loop | StateGraph Orchestration | `app/workflow/graph.py`, `app/workflow/nodes/` | `tests/workflow/test_workflow.py` | `test_workflow_happy_path`, `test_workflow_sse_streaming` | PASS |
| **13.1 - 13.2** | Deterministic Verifier (Rules 1-6) enforcing 100% Claim Grounding | Rules Engine & Judge Rubric | `app/workflow/verifier.py` | `tests/workflow/test_workflow.py` | `test_workflow_happy_path` (100% evidence coverage verified) | PASS |
| **14.0** | Security Guardrails (Injection, Off-Topic, Range, Novel Type) | Regex & Heuristic Gate | `app/core/guardrails.py`, `app/workflow/nodes/gate.py` | `tests/unit/test_guardrails.py` | `test_guardrails_injection_rejection`, `test_workflow_injection_rejection` | PASS |
| **15.0** | FastAPI Application & REST Endpoints with SSE Streaming | FastAPI & StreamingResponse | `app/main.py`, `app/api/routes.py` | `tests/api/test_api.py` | `test_analyze_endpoint_happy_path`, `test_health_endpoint` | PASS |
| **16.0** | Streamlit UI Dashboard & Persistent Modes Banner | Streamlit & Plotly | `ui/app.py`, `ui/pages/` | `tests/ui/test_ui.py` | Headless port 8501 probe (HTTP 200 OK) | PASS |
| **17.1 - 17.6** | Evaluation Harness, DeepEval Suite, Ablation Benchmarks | DeepEval / FakeJudge | `evaluation/report.py`, `deepeval_suite.py`, `ablation.py` | `tests/eval/test_eval.py` | `artifacts/reports/EVALUATION_REPORT.md`, `docs/EVALUATION.md` | PASS |
| **18.0** | Continuous Feedback Store, Review Queue, Retrain Gate | SQLite & Champion-Challenger | `app/feedback/store.py`, `scripts/retrain_gate.py`, `replay_feedback_experiment.py` | `tests/feedback/test_feedback.py` | `artifacts/reports/feedback_replay_report.md` | PASS |
