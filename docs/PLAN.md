# Implementation Plan: AI-Powered Supply Chain Disruption Assistant

## 1. Build Order
The system is constructed across eleven sequential phases (Phases 0 through 10) under the protocol:
`PLAN -> BUILD -> TEST -> SELF-REVIEW -> FIX -> COMMIT -> PHASE REPORT`.

1. **Phase 0 (Bootstrap & Setup):** Dual virtual environments (`.venv` runtime, `.venv-eval` evaluation), directory skeleton, developer CLI (`scripts/dev.py`), environment check (`scripts/env_check.py`), library smoke tests, and plan critique.
2. **Phase 1 (Core, Config, Logging, Schemas):** Typed Pydantic v2 domain schemas, configuration layer with `.env` / YAML loaders, security/redaction filters, correlation IDs, and runtime mode banner.
3. **Phase 2 (Data Pipeline & Stratified Sampling):** Raw dataset handling (or schema-faithful synthetic fallback), cleaning and normalization, parquet ledger and SQLite mirror, stratification (80/10/10 train/val/test and 20% calibration slice), EDA signal check, deterministic case card builder, derived playbooks, data dictionary, and stratified Synapt sample generation.
4. **Phase 3 (Substrate Layer):** Read, feedback, and admin gateways; MCP adapter, mock adapter, and replay adapter; Cypher templates with composite keys and parameter binding; probe tool with content state detection; fixtures recording and graph audit scripts.
5. **Phase 4 (LLM Layer):** LiteLLM multi-provider router (Gemini free, OpenRouter free), token bucket rate limiting with tenacity jitter, SQLite response caching, structured output extractor with single-retry repair, and deterministic FakeLLM fallback.
6. **Phase 5 (Basic Requirements Core Services):** Hybrid retrieval engine (reciprocal rank fusion over 4 signals: Cypher overlap, node search, chunk search, exact match), relaxation ladder, classification service with abstention, disruption prioritisation, evidence-grounded response recommendations, input guardrails, and core FastAPI endpoints.
7. **Phase 6 (Machine Learning & Resilience):** ColumnTransformer regression pipelines (Dummy, Ridge, RandomForest, HistGradientBoosting) for production impact, log-loss, and recovery days; split-conformal prediction intervals (80% nominal coverage); TreeExplainer SHAP explainability with permutation fallback; conditional severity risk and resilience index; analog comparison with sample vs full-ledger divergence warnings.
8. **Phase 7 (Multi-Agent Workflow):** LangGraph state machine orchestrating Gate, Intake, Classify, Investigate, Impact, Response, Recovery, Synthesize, and Verifier nodes; strict evidence type contract; repair loop (max 2 iterations); SSE streaming and SQLite run trace persistence.
9. **Phase 8 (Evaluation & Continuous Improvement):** DeepEval test harness in isolated `.venv-eval`, ablation runner (A: LLM only, B: chunks only, B2: query only, C: inspect lane, D: full workflow), LLM-as-judge with rubric, guardrails evaluation suite, SQLite feedback store, feedback review CLI, retrain champion-challenger gate, and replay experiment.
10. **Phase 9 (Streamlit User Interface):** Five interactive dashboards (New Disruption intake, In-depth Analysis with evidence chips and SHAP charts, Priority Queue, Feedback capture, Quality/Evaluation metrics) with persistent mode indicators.
11. **Phase 10 (Hardening, Traceability & Final Documentation):** Comprehensive documentation suite (`ARCHITECTURE.md`, `DESIGN.md`, `TRACEABILITY.md`, `API.md`, `DATA.md`, `EVALUATION.md`, `PRESENTATION_OUTLINE.md`, `USER_ACTIONS.md`, `FINAL_REPORT.md`), Docker configuration, end-to-end smoke verification (`scripts/e2e_smoke.py`), and release checks.

---

## 2. The 12 Most Likely Failure Modes and Prevention Strategies

1. **Substrate Retrieval Failure / Empty Substrate:**
   - *Failure:* Synapt endpoint unreachable or query yields zero matches.
   - *Prevention:* Fail-closed architecture. Return `status="degraded"` with quantitative predictions and priority only, explicitly omitting recommendations and recording knowledge gaps. Never invent facts.
2. **Rate Limit / Free-Tier Quota Exhaustion on LLMs:**
   - *Failure:* Free Gemini or OpenRouter endpoints return HTTP 429 during workflow or evaluation.
   - *Prevention:* Per-provider token-bucket rate limiter, local SQLite response cache, tenacity exponential backoff with jitter, budget caps per run (max 8 LLM calls), and automatic fallback to `FakeLLM`.
3. **Severe Label Collisions ("Medium" Severity vs "Medium" Supplier Size):**
   - *Failure:* Cypher queries conflate node properties or semantic search mixes supplier size with disruption severity.
   - *Prevention:* Use composite keys `type:label` (e.g., `severity:Medium` vs `supplier_size:Medium`) in graph queries, explicit narrative phrasing in case cards, and collision audit in `audit_graph.py`.
4. **Evaluation Data Leakage:**
   - *Failure:* Evaluating retrieval or LLM nodes on cases already present in the Synapt knowledge base.
   - *Prevention:* Split before ingestion. Train split only is ingested into Synapt; validation and test sets remain strictly disjoint and held out. Probe identifies ingested IDs and filters evaluation sets accordingly.
5. **Windows Path and Encoding Incompatibilities:**
   - *Failure:* Backslash path errors, cp1252 character decode failures, or emoji print errors in Windows PowerShell.
   - *Prevention:* Enforce `pathlib.Path`, explicit `encoding="utf-8"` on all file I/O, `PYTHONUTF8=1` in subprocess runners, and strict ASCII-only terminal output.
6. **Strict Tool-Calling Failures on Free LLMs:**
   - *Failure:* Small free models fail to execute complex tool-call schemas reliably.
   - *Prevention:* Deterministic orchestration. Python code determines and executes all substrate tool plans; LLMs are passed structured evidence and tasked solely with language generation and structured JSON extraction.
7. **Hallucinated Historical Facts or Unjustified Numbers:**
   - *Failure:* LLM invents historical analogies or hallucinates statistical figures not in the data.
   - *Prevention:* Typed Evidence contract (`HISTORICAL_FACT`, `DATASET_STATISTIC`, `MODEL_ESTIMATE`). Verifier checks that every historical fact cites an existing evidence ID and all statistics match ledger calculations.
8. **Dependency Hell Between DeepEval and LangGraph/LiteLLM:**
   - *Failure:* Transitive dependencies of DeepEval conflict with core runtime packages.
   - *Prevention:* Complete environment isolation. Dual venvs: `.venv` for the application service and `.venv-eval` for DeepEval. Evaluation communicates exclusively over HTTP or via persisted JSON run artifacts.
9. **Prompt Injection via Case Narrative or User Input:**
   - *Failure:* Adversarial text in user input or retrieved case descriptions alters model instructions.
   - *Prevention:* Multi-layer guardrails. Input gate regex checks, structural XML-style delimiters around retrieved evidence, and explicit system prompt rules ignoring instructions embedded within evidence.
10. **Conformal Interval Breakdown on Extreme Targets:**
    - *Failure:* Residuals of skewed revenue loss break prediction intervals.
    - *Prevention:* Train models on `log1p(revenue_loss_usd)`, invert predictions, and calibrate empirical non-conformity scores on a dedicated 20% calibration split with 80% nominal coverage.
11. **Accidental Ingestion or Destructive Substrate Mutations:**
    - *Failure:* Runtime service invoking `trident_ingest` or destructive entity creation.
    - *Prevention:* Rigid gateway tier separation (`SynaptReadGateway` vs `SynaptAdminGateway`). Runtime app never imports Admin gateway; enforced by unit tests.
12. **Slow Execution on 100k-Row Dataset:**
    - *Failure:* Iterative Python loops over 100,000 rows cause timeouts.
    - *Prevention:* Vectorized pandas and pyarrow operations for the ledger; subsampled SHAP calculations (max 2,000 rows); bounded stratified Synapt sample (default 500 cases).

---

## 3. Critique Round: First Run on Fresh Windows Laptop with Free Keys

**Critique Question:**
*What would make this project fail on first run on a fresh Windows laptop with free API keys?*

**Vulnerabilities Identified & Concrete Fixes Applied:**
1. *PowerShell Command Invocation & Relative Paths:* In PowerShell, executing python scripts without `&` or using relative paths can stall or behave inconsistently.
   - *Fix:* Ensure all CLI wrappers and subprocess invocations in `scripts/dev.py` use resolved absolute paths and explicitly set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`.
2. *Missing Keys / First-Run Crashes:* If a user starts the app before providing API keys, unhandled `None` environment variables could throw validation errors.
   - *Fix:* Graceful degradation by design. `app/core/config.py` defaults to `LLM_MODE=fake` and `SYNAPT_MODE=mock` when credentials are empty, displaying clear startup status banners rather than crashing.
3. *LiteLLM Provider Syntax Variations:* Different free models on OpenRouter or Gemini may reject certain parameter configurations or JSON schemas.
   - *Fix:* `probe_models.py` verifies each candidate model with an actual micro-call before activating it, saving verified models to `config/models.resolved.yaml`. Prompt extraction includes a defensive Pydantic validator with single-retry correction before falling back to templated JSON.
4. *SHAP C-extension Compilation Issues on Windows Python 3.12:*
   - *Fix:* Import of SHAP is wrapped in try/except; if tree explainer fails or crashes, explainability automatically falls back to scikit-learn permutation importance without breaking the pipeline.
