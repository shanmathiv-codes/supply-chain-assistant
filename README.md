# 🚢 AI-Powered Supply Chain Disruption Investigation System

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.42+-FF4B4B.svg)](https://streamlit.io/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-purple.svg)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An enterprise-grade, agentic AI assistant for supply chain disruption triage, analog investigation, split-conformal impact prediction, and evidence-grounded response planning—powered by **Synapt's Trident Graph & Knowledge Engine via Model Context Protocol (MCP)**.

---

## 🌟 Key Capabilities

1. **4-Signal Hybrid Retrieval:** Fuses structured Cypher attribute overlap, semantic node search, unstructured text chunk mining, and exact entity resolution via Reciprocal Rank Fusion (RRF).
2. **LangGraph Multi-Agent Workflow:** Directed 9-node state graph orchestrating intake, classification, retrieval, ML impact estimation, response planning, and report synthesis.
3. **Deterministic Verifier & Repair Loop:** Enforces 6 strict validation rules and an automated revision loop (max 2 iterations). Guarantees **100% evidence citation grounding** on all historical fact claims.
4. **Split-Conformal Calibration:** Delivers honest, distribution-free 80% prediction intervals on production impact, financial loss, and recovery duration (empirically attaining 80.0% coverage on test cases).
5. **Formula-Grounded Prioritization:** Triage scoring $P = 100 \cdot (w_s S + w_p I + w_f F)$ with P1-P4 bands and weight-sensitivity perturbation analysis.
6. **Continuous Human Feedback Loop:** Human review queue, case card staging, champion-challenger retraining gate, and simulated replay experiments.
7. **Offline Gracefulness:** Seamless local mock substrate, FakeLLM generators, and SHA-256 SQLite prompt caching—guaranteeing 100% test passability without external API dependencies.

---

## 🏗️ Architecture at a Glance

```
User Alert / Free Text
         │
         ▼
┌──────────────────┐
│ Security Gate    │ ── Reject (Prompt Injection / Off-Topic / Malformed)
└──────────────────┘
         │
         ▼
┌──────────────────┐
│ Intake & Classify│ ── Extract taxonomy & ensemble voting (Abstain on conflict)
└──────────────────┘
         │
         ▼
┌──────────────────┐
│ Hybrid Retrieval │ ── Synapt MCP (Cypher Overlap + Search + Chunks + Exact)
└──────────────────┘
         │
    ┌────┴──────────────────────────┐
    ▼                               ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│ ML & Conformal Predict  │   │ SOP Response Planning   │
│ (80% Prediction Ranges) │   │ (Playbooks & Outcomes)  │
└─────────────────────────┘   └─────────────────────────┘
    │                               │
    └────┬──────────────────────────┘
         ▼
┌──────────────────┐
│ Report Synthesis │
└──────────────────┘
         │
         ▼
┌──────────────────┐
│ Verifier Check   │ ── Violations? ──► Repair Loop (Max 2 revisions)
└──────────────────┘
         │ Passed
         ▼
┌────────────────────────────────────────────────────────┐
│ Final Investigation Report (JSON / Markdown / Stream)  │
└────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.12+ installed
- Git
- Windows PowerShell or Bash (Linux / macOS)

### 1. Clone & Bootstrap Environment
```powershell
# Windows PowerShell
git clone https://github.com/your-org/supply-chain-project.git
cd supply-chain-project

# Run developer setup (checks environments and dependencies)
& .venv\Scripts\python.exe -m scripts.dev setup
```

```bash
# Linux / macOS
git clone https://github.com/your-org/supply-chain-project.git
cd supply-chain-project

python3 -m scripts.dev setup
```

### 2. Run Data Pipeline & Train Models
```powershell
# Run data pipeline (processes raw CSV or generates synthetic fallback)
& .venv\Scripts\python.exe -m scripts.dev data --source auto

# Train ML regressors, classifiers, and split-conformal calibration
& .venv\Scripts\python.exe -m scripts.dev train --final
```

### 3. Run Automated Tests & E2E Smoke Verification
```powershell
# Run offline test suite (57 tests passing in ~7s)
& .venv\Scripts\python.exe -m scripts.dev test

# Run end-to-end smoke test (spins up API on ephemeral port, calls /analyze, verifies 100% claim grounding)
& .venv\Scripts\python.exe -m scripts.dev e2e
```

### 4. Start Application Services

#### Terminal 1: Launch FastAPI Backend (Port 8000)
```powershell
& .venv\Scripts\python.exe -m scripts.dev api --port 8000
```
- API Docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

#### Terminal 2: Launch Streamlit UI (Port 8501)
```powershell
& .venv\Scripts\python.exe -m scripts.dev ui
```
- Dashboard: `http://localhost:8501`

---

## 🧪 Developer CLI (`scripts/dev.py`) Reference

| Command | Description |
| :--- | :--- |
| `python -m scripts.dev setup` | Verify dependencies and environment readiness |
| `python -m scripts.dev data --source auto` | Execute acquire -> clean -> splits -> cards -> playbooks pipeline |
| `python -m scripts.dev sample --size 500` | Generate stratified 500-case Synapt ingestion sample |
| `python -m scripts.dev train --final` | Train ML models and evaluate on held-out test split |
| `python -m scripts.dev test` | Run complete offline pytest suite |
| `python -m scripts.dev e2e` | Run end-to-end integration smoke test |
| `python -m scripts.dev api` | Start FastAPI service on port 8000 |
| `python -m scripts.dev ui` | Start Streamlit UI on port 8501 |
| `python -m scripts.dev eval --budget small` | Run DeepEval & ablation benchmark harness |
| `python -m scripts.dev probe-models` | Test available free Gemini & OpenRouter endpoints |
| `python -m scripts.dev synapt-probe` | Probe Synapt MCP tools, schema, and provider health |
| `python -m scripts.dev warm-cache` | Pre-warm SQLite LLM prompt cache with golden scenarios |

---

## 🐳 Docker Deployment

Run the complete multi-service architecture using Docker Compose:

```bash
docker-compose up --build
```
- FastAPI API will be available at `http://localhost:8000`
- Streamlit UI will be available at `http://localhost:8501`

---

## 📚 Technical Documentation Index

- [System Architecture (Mermaid Diagrams)](docs/ARCHITECTURE.md)
- [System Design & Mathematical Rationale](docs/DESIGN.md)
- [Requirements Traceability Matrix](docs/TRACEABILITY.md)
- [REST API Reference & Curl Examples](docs/API.md)
- [Data Pipeline & Knowledge Packs](docs/DATA.md)
- [System Evaluation & Benchmark Report](docs/EVALUATION.md)
- [Executive 10-Minute Presentation Outline](docs/PRESENTATION_OUTLINE.md)
- [Operator Run Book & Production Setup](docs/USER_ACTIONS.md)
- [Project Progress & Verification History](docs/PROGRESS.md)
- [Phase 10 Final Comprehensive Report](docs/FINAL_REPORT.md)

---

## ⚖️ Scientific Boundaries & Disclaimers

1. **Non-Causal Associations:** All findings reflect statistical associations observed in historical incident records. The system avoids asserting deterministic causality.
2. **Conditional Resilience:** The historical dataset records disruption events only; the unconditional prior $P(\text{disruption occurs})$ is mathematically unestimable and never reported. All metrics reflect conditional risk given an event.
3. **Directional Metrics:** Supplier change classification achieves ROC-AUC 0.657 and is explicitly labeled as directional guidance only.
