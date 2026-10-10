# REST API Reference & Usage Guide

> **Base URL:** `http://127.0.0.1:8000`  
> **Interactive Documentation:** `http://127.0.0.1:8000/docs` (OpenAPI Swagger)  
> **Alternative Documentation:** `http://127.0.0.1:8000/redoc` (ReDoc)  

---

## 1. Authentication & Headers

When `API_KEY` is set in configuration, all requests must provide the key via the `X-API-Key` header:
- `X-API-Key: <your-api-key>`
- `Content-Type: application/json`

### Error Response Format
All endpoint errors return standardized JSON payloads:
```json
{
  "error": {
    "code": "VALIDATION_ERROR | INJECTION_SUSPECTED | OFF_TOPIC | NOT_FOUND | RATE_LIMITED",
    "message": "Human-readable description of error.",
    "details": {}
  }
}
```

---

## 2. API Endpoints

### 2.1 Health Check & Runtime Modes
- **Endpoint:** `GET /health`
- **Description:** Returns service status, active runtime modes (MOCK/LIVE/FAKE/SYNTHETIC), loaded model versions, and substrate status.

#### Examples
**Bash / cURL:**
```bash
curl -X GET "http://127.0.0.1:8000/health"
```

**PowerShell (Windows):**
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get
```

---

### 2.2 Full Disruption Investigation Workflow
- **Endpoint:** `POST /disruptions/analyze`
- **Query Params:** `?stream=true` (optional SSE event stream)
- **Description:** Executes the full 9-node LangGraph multi-agent workflow including guardrails, intake, classification, 4-signal hybrid retrieval, ML prediction, response planning, and deterministic verification.

#### Request Body
```json
{
  "profile": {
    "disruption_type": "Port Closure",
    "disruption_severity": "High",
    "industry": "Automotive",
    "supplier_region": "APAC",
    "supplier_tier": "Tier 1",
    "supplier_size": "Large",
    "has_backup_supplier": "Yes"
  },
  "free_text": "Typhoon alert causing terminal closure in East Asia port."
}
```

#### Examples
**Bash / cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/disruptions/analyze" \
  -H "Content-Type: application/json" \
  -d '{"profile": {"disruption_type": "Port Closure", "disruption_severity": "High", "industry": "Automotive", "supplier_region": "APAC", "supplier_tier": "Tier 1", "supplier_size": "Large", "has_backup_supplier": "Yes"}}'
```

**PowerShell (Windows):**
```powershell
$body = @{
    profile = @{
        disruption_type = "Port Closure"
        disruption_severity = "High"
        industry = "Automotive"
        supplier_region = "APAC"
        supplier_tier = "Tier 1"
        supplier_size = "Large"
        has_backup_supplier = "Yes"
    }
    free_text = "Port closure affecting Tier 1 automotive parts."
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri "http://127.0.0.1:8000/disruptions/analyze" -Method Post -ContentType "application/json" -Body $body
```

---

### 2.3 Machine Learning Predictions & Conformal Intervals
- **Endpoint:** `POST /disruptions/predict`
- **Description:** Returns point estimates, 80% split-conformal bounds, top predictive feature attributions, and historical analog divergence flags.

#### Request Body
```json
{
  "profile": {
    "disruption_type": "Factory Fire",
    "industry": "Electronics",
    "supplier_region": "Europe",
    "supplier_tier": "Tier 2",
    "supplier_size": "Medium",
    "has_backup_supplier": "No"
  }
}
```

#### Examples
**Bash / cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/disruptions/predict" \
  -H "Content-Type: application/json" \
  -d '{"profile": {"disruption_type": "Factory Fire", "industry": "Electronics", "supplier_region": "Europe", "supplier_tier": "Tier 2", "supplier_size": "Medium", "has_backup_supplier": "No"}}'
```

**PowerShell (Windows):**
```powershell
$body = @{
    profile = @{
        disruption_type = "Factory Fire"
        industry = "Electronics"
        supplier_region = "Europe"
        supplier_tier = "Tier 2"
        supplier_size = "Medium"
        has_backup_supplier = "No"
    }
} | ConvertTo-Json -Depth 4

Invoke-RestMethod -Uri "http://127.0.0.1:8000/disruptions/predict" -Method Post -ContentType "application/json" -Body $body
```

---

### 2.4 Similar Case Hybrid Search
- **Endpoint:** `POST /disruptions/search`
- **Description:** Retrieves analog historical disruption cases using 4-signal hybrid fusion (Cypher structured overlap, semantic node search, chunk text search, and exact matching) with Reciprocal Rank Fusion.

#### Request Body
```json
{
  "profile": {
    "disruption_type": "Cyberattack",
    "industry": "Pharmaceuticals",
    "supplier_region": "North America"
  },
  "top_k": 5,
  "relax_ladder": true
}
```

#### Examples
**PowerShell (Windows):**
```powershell
$body = @{
    profile = @{
        disruption_type = "Cyberattack"
        industry = "Pharmaceuticals"
        supplier_region = "North America"
    }
    top_k = 5
} | ConvertTo-Json -Depth 4

Invoke-RestMethod -Uri "http://127.0.0.1:8000/disruptions/search" -Method Post -ContentType "application/json" -Body $body
```

---

### 2.5 Disruption Prioritization
- **Endpoint:** `POST /disruptions/prioritize`
- **Description:** Computes formula-grounded priority score $P = 100 \cdot (w_s S + w_p I + w_f F)$, assigns P1-P4 triage band, and executes sensitivity perturbation tests.

#### Examples
**PowerShell (Windows):**
```powershell
$body = @{
    severity = "High"
    production_impact_pct = 35.0
    revenue_loss_usd = 600000.0
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/disruptions/prioritize" -Method Post -ContentType "application/json" -Body $body
```

---

### 2.6 Disruption Classification
- **Endpoint:** `POST /disruptions/classify`
- **Description:** Ensemble classification combining neighbor voting, keyword matching, and LLM classification with conflict abstention.

---

### 2.7 Case Record Retrieval
- **Endpoint:** `GET /cases/{case_id}`
- **Description:** Retrieves the complete structured ledger record and associated Synapt graph evidence for an individual case.

#### Examples
**PowerShell (Windows):**
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/cases/DIS-00123" -Method Get
```

---

### 2.8 Investigation Run Retrieval
- **Endpoint:** `GET /runs/{run_id}`
- **Description:** Fetches stored investigation report, state trace, and timing logs from SQLite store.

---

### 2.9 Submit Feedback & Outcomes
- **Endpoint:** `POST /feedback`
- **Description:** Submits qualitative operator ratings or logs actual post-incident outcomes into the human review queue.

#### Request Body
```json
{
  "run_id": "RUN-DEMO-001",
  "kind": "relevance",
  "value": 5.0,
  "comment": "Secondary sourcing recommendation matches our contractual playbook."
}
```

#### Examples
**PowerShell (Windows):**
```powershell
$body = @{
    run_id = "RUN-DEMO-001"
    kind = "relevance"
    value = 5.0
    comment = "Secondary sourcing recommendation matches our contractual playbook."
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/feedback" -Method Post -ContentType "application/json" -Body $body
```

---

### 2.10 Evaluation Summary
- **Endpoint:** `GET /evaluations`
- **Description:** Returns the latest evaluation benchmarks, ablation results, and DeepEval scores.
