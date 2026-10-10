# System Architecture & Technical Specifications

> **System Name:** AI-Powered Supply Chain Disruption Investigation Assistant  
> **Substrate Engine:** Synapt (Trident Knowledge & Graph Engine via Model Context Protocol)  
> **Workflow Orchestration:** LangGraph Multi-Agent StateGraph  
> **Predictive Machine Learning:** Split-Conformal Calibrated HistGradientBoosting & Ridge Regressors  

---

## 1. High-Level Architectural Overview

The Supply Chain Disruption Assistant is an enterprise-grade agentic system designed to triage, investigate, predict, and mitigate operational disruptions across global supply networks. The architecture enforces an uncompromising **Evidence Contract**: no factual claim or mitigation recommendation can be surfaced to the user without direct provenance in the Synapt graph substrate or validated case ledger.

```mermaid
flowchart TD
    subgraph UI ["User Experience Layer (Streamlit)"]
        A1["1. New Disruption Intake"]
        A2["2. Multi-Tab Analysis View"]
        A3["3. Priority Triage Queue (P1-P4)"]
        A4["4. Operator Feedback Loop"]
        A5["5. Scientific Quality & Ablation"]
    end

    subgraph API ["Application Services (FastAPI)"]
        B1["Security Guardrails Gate"]
        B2["REST Endpoints (/analyze, /predict, /search, /prioritize)"]
        B3["SSE Streaming Engine"]
        B4["Run Store (SQLite app.db)"]
        B5["Feedback Store (SQLite feedback.db)"]
    end

    subgraph Workflow ["Multi-Agent Graph (LangGraph)"]
        C1["gate"] --> C2["intake"]
        C2 --> C3["classify"]
        C3 --> C4["investigate"]
        C4 --> C5["impact"]
        C4 --> C6["response_plan"]
        C5 --> C7["recovery"]
        C6 --> C7
        C7 --> C8["synthesize"]
        C8 --> C9{"verify\n(Rules 1-6 + Judge)"}
        C9 -- "Fix List (max 2)" --> C8
        C9 -- "Approved / Degraded" --> C10["PERSIST & EMIT"]
    end

    subgraph Substrate ["Synapt Substrate Tier (MCP Gateway)"]
        D1["SynaptReadGateway\n(12 Read Tools)"]
        D2["SynaptFeedbackGateway\n(trident_feedback)"]
        D3["SynaptAdminGateway\n(trident_ingest - Scripts Only)"]
        D4["Adapters: MCP / Replay / Mock"]
    end

    subgraph Models ["Predictive Intelligence (Scikit-Learn)"]
        E1["Impact Regressor (HistGradientBoosting)"]
        E2["Loss Regressor (Ridge log1p)"]
        E3["Recovery Regressor (HistGradientBoosting)"]
        E4["Split-Conformal Calibrator (80% Nominal)"]
        E5["Severity & Supplier Classifiers"]
        E6["TreeExplainer & Permutation Attribution"]
    end

    UI --> API
    API --> Workflow
    Workflow --> Substrate
    Workflow --> Models
```

---

## 2. LangGraph Multi-Agent Workflow Sequence

The investigation workflow executes a directed state graph where intermediate nodes produce typed findings into `WorkflowState`. A deterministic verifier inspects all claims before publishing.

```mermaid
sequenceDiagram
    autonumber
    actor User as Operator / Client
    participant Gate as Gate Node
    participant Intake as Intake Node
    participant Classify as Classify Node
    participant Investigate as Investigate Node
    participant Substrate as Synapt Substrate
    participant ML as ML & Conformal Models
    participant Plan as Response Plan Node
    participant Synth as Synthesize Node
    participant Verifier as Verifier Node
    participant Store as Run Store

    User->>Gate: POST /disruptions/analyze
    Gate->>Gate: Guardrails Check (Injection, Range, PII)
    Gate->>Intake: Sanitized Payload
    Intake->>Classify: Disruption Profile
    Classify->>Investigate: Ensemble Type & Severity
    Investigate->>Substrate: 4-Signal Hybrid Retrieval (Cypher, Chunks, Search, Exact)
    Substrate-->>Investigate: Top Analog Cases & SOP Procedures
    par Parallel Investigation
        Investigate->>ML: Profile Features (T0)
        ML-->>ML: Predict Point Estimates + Conformal Intervals (80%)
    and Response Planning
        Investigate->>Plan: Analog Response Outcomes & SOP Playbooks
        Plan-->>Plan: Formulate Evidence-Grounded Mitigations
    end
    ML->>Synth: Impact, Loss, Recovery, Resilience
    Plan->>Synth: Draft Response Actions & Claims
    Synth->>Verifier: Draft Investigation Report
    Verifier->>Verifier: Check Rules 1-6 (Evidence IDs, Numbers, Non-causal Tone)
    alt Verification Passed
        Verifier->>Store: Save Report, Substrate Trace, Latency
        Store-->>User: HTTP 200 Final InvestigationReport
    else Verifier Found Violations (Revision < 2)
        Verifier->>Synth: Fix List (Remove ungrounded claims, fix intervals)
        Synth->>Verifier: Revised Draft
        Verifier->>Store: Save Verified / Degraded Report
        Store-->>User: HTTP 200 Final InvestigationReport
    end
```

---

## 3. Four-Signal Hybrid Retrieval Architecture

To overcome the limitations of isolated text search or rigid graph queries, retrieval executes four distinct signals against Synapt, combined via Reciprocal Rank Fusion (RRF):

```mermaid
flowchart LR
    Q["Incident Query"] --> S1["Signal 1: Structured Cypher\n(attr_overlap_rank)"]
    Q --> S2["Signal 2: Semantic Node Search\n(trident_search)"]
    Q --> S3["Signal 3: Unstructured Chunk Search\n(trident_get_chunks)"]
    Q --> S4["Signal 4: Exact Entity Lookup\n(trident_find_exact)"]

    S1 --> F["Reciprocal Rank Fusion (RRF)\nscore = sum(w_s / (60 + rank_s))"]
    S2 --> F
    S3 --> F
    S4 --> F

    F --> L{"Candidate Count ≥ min_cases?"}
    L -- "Yes" --> RES["Fused Ranked Cases\n(with Signal Attribution)"]
    L -- "No" --> REL["Filter Relaxation Ladder\nDrop: Size -> Region -> Tier -> Industry"]
    REL --> S1
```

---

## 4. Machine Learning & Split-Conformal Calibration Architecture

```mermaid
flowchart TD
    subgraph Data ["Data Split Architecture (Zero Leakage)"]
        RAW["Cleaned Dataset (100,000 cases)"] --> TR["Train Fit Split (64,000 cases)"]
        RAW --> CAL["Calibration Split (16,000 cases)"]
        RAW --> VAL["Validation Split (10,000 cases)"]
        RAW --> TST["Test Split (10,000 cases)"]
    end

    subgraph Training ["Model Training & Calibration"]
        TR --> TRAIN["Train Regressors (CV MAE Selection)\n- HistGradientBoosting\n- Ridge log1p"]
        TRAIN --> RESID["Compute Non-Conformity Scores on CAL\nR_i = |y_i - y_hat_i|"]
        CAL --> RESID
        RESID --> QUANT["Compute Empirical Quantile q_val\nLevel: 1 - alpha = 0.80"]
    end

    subgraph Inference ["Production Inference"]
        NEW["New Disruption Profile"] --> PRED["Point Estimate y_hat"]
        QUANT --> INT["Conformal Interval\n[y_hat - q_val, y_hat + q_val]"]
        PRED --> INT
        INT --> COV["Empirical Test Coverage: 80.0%"]
    end
```

---

## 5. Security & Permission Boundary Architecture

The architecture enforces a strict privilege boundary across runtime tiers:
1. **User Tier:** Only accesses `SynaptReadGateway` and `SynaptFeedbackGateway`.
2. **Admin Tier (`scripts/ingest_to_synapt.py`):** Holds access to `SynaptAdminGateway` (`trident_ingest`).
3. **Automated Enforcement:** Verified by unit test `test_admin_gateway_import_ban` ensuring no module inside `app/` imports `SynaptAdminGateway`.
