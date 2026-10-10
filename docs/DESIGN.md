# System Design & Implementation Rationale

> **Document Version:** 1.0.0  
> **Target Audience:** Lead Architects, Systems Engineers, Supply Chain Operators  

---

## 1. Core Design Principles

The Supply Chain Disruption Investigation System is engineered around six non-negotiable architectural tenets:

### 1.1 The Evidence Contract
Traditional LLM systems frequently hallucinate plausible-sounding statistics, timelines, and case precedents. In this system:
- **No ungrounded factual assertions:** Every statement of kind `HISTORICAL_FACT` must cite an explicit `evidence_id` mapped to an underlying Synapt graph node or text passage.
- **Strict Verifier Enforcement:** The deterministic verifier scans all claims before report release. Any claim failing citation validation triggers a repair cycle; unresolvable claims are purged before publication.

### 1.2 Non-Causal Statistical Integrity
Disruption datasets capture observational associations rather than randomized controlled trials.
- **Language Policy:** The system enforces non-causal language. Causal terms ("caused by", "because of", "guarantees") are strictly barred in statistical contexts. All effects are described as "associated with" or "observed historically under".
- **Conditionality Notice:** Disruption datasets contain only disruption records. Therefore, unconditional prior probabilities ($P(\text{disruption occurs})$) cannot be calculated and are never asserted. The system strictly estimates conditional severity $P(\text{severity} \ge \text{High} \mid \text{event})$.

### 1.3 Split-Conformal Prediction Intervals
Point estimates create a false illusion of precision. We provide distribution-free prediction intervals with guaranteed 80% coverage:
- Residuals are measured on a separate, held-out `calibration` split (16,000 cases).
- Non-conformity quantiles yield honest bounds $[y_{\text{low}}, y_{\text{high}}]$ that empirically attain 80.0% coverage on test cases.

### 1.4 Resilient Multi-Tier Graceful Degradation
Enterprise systems must not crash when external dependencies fail.
- When Synapt credentials are absent, the system seamlessly activates the `mock` adapter.
- When LLM API keys are absent, the system activates `FakeLLM` with deterministic templates.
- When zero historical analogs match a query, the workflow does NOT invent recommendations; it returns `status="degraded"` with explicit `knowledge_gaps=["no historical evidence available"]`.

### 1.5 Strict Separation of Privilege Tiers
- Runtime application services (`app/`) are physically barred from importing `SynaptAdminGateway` (`trident_ingest`). Ingestion is restricted to operator scripts requiring explicit confirmation.

---

## 2. Key Component Design

### 2.1 Substrate Gateway Tier (`app/substrate/`)
The gateway translates abstract domain requests into Synapt Model Context Protocol (MCP) calls:
- **Dynamic Adapters:** Implements `mcp_adapter.py` (real MCP client), `replay_adapter.py` (offline deterministic recorded fixtures), and `mock_adapter.py` (in-memory TF-IDF and pandas graph stand-in).
- **Parameterized Cypher Templates:** LLMs are never permitted to compose raw Cypher. All queries execute through audited template files with regex parameter binding and injection protection (`$provider_id`, `$exclude_case_ids`).
- **Resilience Controls:** Timeouts, exponential backoff jitter, circuit breaking after sequential failures, and in-memory TTL caching.

### 2.2 LLM Orchestration Tier (`app/llm/`)
- **LiteLLM Router:** Routes calls across `fast` (intake/classify), `reason` (planning/recovery/synthesis), and `judge` (verification) roles with automatic fallback.
- **Offline Safety Flags:** Automatic enforcement of `LITELLM_LOCAL_MODEL_COST_MAP=True` and `LITELLM_DISABLE_TELEMETRY=True` to prevent hangs on isolated networks.
- **Structured JSON Repair:** Rather than trusting free-form JSON mode, prompts include explicit JSON schemas, extract the first valid JSON block, validate via Pydantic, and execute one targeted repair on validation failure.

### 2.3 Prioritization Mathematical Framework (`app/services/prioritization.py`)
Priority triage is computed deterministically:
$$P = 100 \cdot (w_s S + w_p I + w_f F)$$
- $S \in [0.25, 1.0]$: Ordinal severity mapping (Low=0.25, Medium=0.50, High=0.75, Critical=1.00).
- $I \in [0.0, 1.0]$: Production impact ratio ($\text{impact\_pct} / 100$).
- $F \in [0.0, 1.0]$: Percentile rank of $\log(1 + \text{loss\_usd})$ within historical distribution.
- Weights: $w_s = 0.40, w_p = 0.35, w_f = 0.25$ (sum = 1.0).
- **Triage Bands:** P1 ($\ge 80$), P2 ($[65, 80)$), P3 ($[40, 65)$), P4 ($< 40$).
- **Sensitivity Perturbation:** Ranks are tested under $\pm 0.1$ weight perturbation to confirm triage band stability.

### 2.4 Human Feedback Loop (`app/feedback/`)
- User feedback and observed operational outcomes are stored with `status="pending"`.
- Pending records are strictly isolated and never fed to models or prompt contexts until approved by human operators via `scripts/review_feedback.py`.
- Approved outcomes trigger the Champion-Challenger tournament via `scripts/retrain_gate.py`, promoting new models only upon verified validation MAE improvement.
