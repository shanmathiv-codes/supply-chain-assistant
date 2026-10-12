# Operator Run Book & Production Transition Guide

> **Current Operational State:** `LLM_MODE=fake`, `SYNAPT_MODE=mock`, `DATASET_SOURCE=synthetic`  
> **Target Production State:** `LLM_MODE=live` (Gemini / OpenRouter), `SYNAPT_MODE=mcp` (Real Trident Knowledge Graph)  

This guide provides step-by-step instructions for operators and administrators transitioning the system from offline evaluation to live production infrastructure.

---

## 1. Environment Variable Configuration (`.env`)

Edit your `.env` file in the project root:

```bash
# -------------------------------------------------------------
# 1. RUNTIME OPERATIONAL MODES
# -------------------------------------------------------------
LLM_MODE=live              # Options: live | fake | cache
SYNAPT_MODE=mcp            # Options: mcp | replay | mock
DATASET_SOURCE=real        # Options: real | synthetic
INGESTION_STATE=user_preingested  # Options: user_preingested | agent_prepared

# -------------------------------------------------------------
# 2. LLM API CREDENTIALS
# -------------------------------------------------------------
GEMINI_API_KEY=your_gemini_api_key_here
# Optional free OpenRouter key:
OPENROUTER_API_KEY=your_openrouter_api_key_here

# -------------------------------------------------------------
# 3. SYNAPT SUBSTRATE CREDENTIALS & MCP URL
# -------------------------------------------------------------
SYNAPT_MCP_URL=https://your-synapt-instance.synapt.io/mcp/
SYNAPT_AUTH_BASE=https://your-synapt-instance.synapt.io/auth/token
SYNAPT_USERNAME=your_username
SYNAPT_PASSWORD=your_password
SYNAPT_PROVIDER_ID=supply_chain_disruption

# -------------------------------------------------------------
# 4. NETWORK & SERVICE CONFIGURATION
# -------------------------------------------------------------
API_HOST=127.0.0.1
API_PORT=8000
API_BASE_URL=http://127.0.0.1:8000
STREAMLIT_PORT=8501
```

When `SYNAPT_MODE=mcp`, the API opens one shared Synapt MCP session during startup and closes it during shutdown. If the initial connection cannot be established, API startup fails with the connection error; correct the Synapt URL or credentials and restart the API.

---

## 2. Model Endpoint Resolution & Probing

Verify which free Gemini or OpenRouter models are available, test structured JSON latency, and resolve working models:

```powershell
# Windows PowerShell
& .venv\Scripts\python.exe -m scripts.dev probe-models
```

This updates `config/models.resolved.yaml` with verified candidate models for `fast`, `reason`, and `judge` roles.

---

## 3. Synapt MCP Connectivity & Schema Probe

Execute the pre-flight Synapt probe:

```powershell
& .venv\Scripts\python.exe -m scripts.dev synapt-probe
```

**Expected Probe Behavior:**
1. Authenticates against `SYNAPT_AUTH_BASE` and extracts a short-lived Bearer token in memory.
2. Lists the 17 MCP tools from `SYNAPT_MCP_URL`.
3. Verifies schema (`trident_get_schema`), provider statistics (`trident_get_stats`), and pattern episodes (`trident_episodes`).
4. Logs detected provider content state (`cases_present` | `partial` | `schema_only`) in `docs/SYNAPT_NOTES.md`.

---

## 4. Ingestion of Knowledge Artifacts into Synapt

If transitioning an empty provider or updating knowledge packs:

### Step 4.1: Ingest Data Dictionary (Definitions & Ontology)
- Upload `dataset/schema_doc/data_dictionary.md` via the Synapt Console (Document Type: `text`).

### Step 4.2: Ingest Sample Case Cards
- Ingest the stratified batch markdown files:
  - `dataset/case_cards/batch_0001.md` through `batch_0005.md` (Document Type: `text`, 1 card per chunk).

### Step 4.3: Ingest Derived SOP Playbooks
- Ingest `dataset/playbooks/*.md` as SOP documents (Document Type: `sop`).

---

## 5. Offline Replay Fixture Recording

To allow downstream developers to run without consuming live Synapt quotas, record a fresh set of replay fixtures:

```powershell
& .venv\Scripts\python.exe -m scripts.dev record-fixtures
```

This saves recorded MCP responses to `fixtures/synapt/real/`. When `SYNAPT_MODE=replay`, the system serves exact recorded responses.

---

## 6. Pre-Warming the LLM Response Cache

Warm the SQLite prompt cache with standard golden scenarios to ensure sub-second demo latency:

```powershell
& .venv\Scripts\python.exe -m scripts.dev warm-cache
```

This populates `dataset/store/llm_cache.db`. When `LLM_MODE=cache`, requests hit the local cache without network calls.

---

## 7. Launching Live Services

### Launch FastAPI Backend:
```powershell
& .venv\Scripts\python.exe -m scripts.dev api --port 8000
```

### Launch Streamlit Dashboard:
```powershell
& .venv\Scripts\python.exe -m scripts.dev ui
```
Open `http://localhost:8501` in your browser. Verify the persistent top banner displays `LIVE` (LLM) and `MCP` (Substrate).

---

## 8. Continuous Improvement & Feedback Administration

### Review Pending Feedback:
```powershell
& .venv\Scripts\python.exe -m scripts.review_feedback list
```

### Approve / Reject an Item:
```powershell
& .venv\Scripts\python.exe -m scripts.review_feedback approve --id <queue_id>
& .venv\Scripts\python.exe -m scripts.review_feedback reject --id <queue_id> --notes "Reason"
```

### Run Retraining Gate:
```powershell
& .venv\Scripts\python.exe -m scripts.retrain_gate --min-samples 10
```
