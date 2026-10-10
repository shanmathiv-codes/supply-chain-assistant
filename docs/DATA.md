# Data Pipeline & Knowledge Artifacts Documentation

> **Dataset Size:** 100,000 incident disruption cases  
> **Storage Formats:** Apache Parquet (`cases_clean.parquet`) & SQLite (`dataset/store/disruptions.db`)  
> **Knowledge Packs:** Case Cards (`dataset/case_cards/`), Derived Playbooks (`dataset/playbooks/`), Data Dictionary (`dataset/schema_doc/`)  

---

## 1. Data Schema & Feature Definitions

The system operates over 15 primary disruption features categorised across operational timelines:

| Column Name | Type | Timeline | Domain Meaning & Allowed Values |
| :--- | :--- | :--- | :--- |
| `disruption_id` | String | T0 (Alert) | Unique case identifier (`DIS-XXXXX`). |
| `disruption_type` | Categorical | T0 (Alert) | Primary root cause: `Port Closure`, `Factory Fire`, `Labor Strike`, `Cyberattack`, `Natural Disaster`, `Raw Material Shortage`, `Geopolitical Conflict`, `Transportation Delay`. |
| `industry` | Categorical | T0 (Alert) | Enterprise sector: `Automotive`, `Aerospace`, `Electronics`, `Pharmaceuticals`, `Retail`, `Energy`, `Logistics`. |
| `supplier_tier` | Categorical | T0 (Alert) | Relationship proximity: `Tier 1` (direct), `Tier 2` (component), `Tier 3` (raw material). |
| `supplier_region` | Categorical | T0 (Alert) | Geographic origin: `APAC`, `North America`, `Europe`, `Latin America`, `Middle East`. |
| `supplier_size` | Categorical | T0 (Alert) | Enterprise footprint: `Small`, `Medium`, `Large`. |
| `has_backup_supplier` | Categorical | T0 (Alert) | Contracted redundancy status: `Yes`, `No`. |
| `disruption_severity` | Categorical | T0 (Alert) | Triage severity level: `Low`, `Medium`, `High`, `Critical`. |
| `production_impact_pct`| Numeric (%) | Outcome | Measured operational loss (0.0 to 100.0%). |
| `revenue_loss_usd` | Numeric ($) | Outcome | Total financial damage in USD (non-negative). |
| `response_type` | Categorical | T1 (Action)| Primary countermeasure: `Dual Sourcing`, `Expedited Freight`, `Inventory Buffer`, `Supplier Assistance`, `Production Re-routing`. |
| `response_time_days` | Numeric | Outcome | Elapsed days between alert and initial intervention. |
| `partial_recovery_days`| Numeric | Outcome | Elapsed days to reach partial operational baseline. |
| `full_recovery_days` | Numeric | Outcome | Total elapsed days to complete recovery. |
| `permanent_supplier_change`| Categorical| Outcome | Whether relationship was severed: `Yes`, `No`. |

---

## 2. Forbidden Columns Policy

To guarantee strict temporal and predictive honesty, the T0 prediction models strictly ban any feature that is only known *after* the incident response has occurred:
- `response_time_days` (Forbidden at T0)
- `partial_recovery_days` (Forbidden at T0)
- `permanent_supplier_change` (Forbidden at T0)
- The target column itself (`production_impact_pct`, `revenue_loss_usd`, or `full_recovery_days`)

This constraint is continuously enforced by automated unit test `test_forbidden_columns_integrity`.

---

## 3. Stratified Splitting Architecture

The 100,000 cases are partitioned using stratified sampling on `(disruption_type, disruption_severity)` to ensure identical segment representation across all subsets:

```
Total Cleaned Dataset (100,000 cases)
├── Train Fit Split (64,000 cases, 64%)  -> Model fitting (cross-validation)
├── Calibration Split (16,000 cases, 16%) -> Split-conformal residual calibration
├── Validation Split (10,000 cases, 10%) -> Hyperparameter tuning & model selection
└── Test Split (10,000 cases, 10%)       -> Final unbiased evaluation (touched once)
```

All split IDs are saved as immutable JSON manifests in `dataset/splits/`:
- `train_ids.json`
- `calibration_ids.json`
- `val_ids.json`
- `test_ids.json`

Splits are mathematically disjoint ($A \cap B = \emptyset$), verified by `test_splits_disjointness`.

---

## 4. Synapt Stratified Ingestion Sample

Synapt is designed to hold a focused, high-fidelity knowledge graph rather than raw database bloat. Therefore:
- Exactly **500 cases** are sampled from the `train_fit` split (`dataset/synapt_sample/sample_ids.json`).
- Zero validation or test cases are ever included in the sample.
- Evaluated held-out benchmarks are strictly drawn from `test.parquet` and verified disjoint from `ingested_ids.json` to eliminate retrieval leakage.

---

## 5. Derived Knowledge Artifacts

### 5.1 Case Cards (`dataset/case_cards/`)
Formatted in machine-readable markdown headers followed by narrative summaries:
```markdown
## Case DIS-00142
disruption_id: DIS-00142 | disruption_type: Port Closure | industry: Automotive | supplier_tier: Tier 1 | supplier_region: APAC | supplier_size: Large | has_backup_supplier: Yes | disruption_severity: High
production_impact_pct: 28.5 | revenue_loss_usd: 380000 | response_type: Dual Sourcing | response_time_days: 3 | partial_recovery_days: 12 | full_recovery_days: 24 | permanent_supplier_change: No

High-severity port closure incident in East Asia affecting a Tier-1 automotive parts supplier. Execution of secondary sourcing mitigated line starvation, restoring full operations in 24 days.
```

### 5.2 Derived Playbooks (`dataset/playbooks/`)
Computed strictly with vectorised pandas aggregations over the entire training set. Each playbook specifies historical response outcomes, milestone quantiles, and permanent supplier change frequencies:
- `playbook_port_closure.md`
- `playbook_factory_fire.md`
- `playbook_labor_strike.md`
- `playbook_cyberattack.md`
- `playbook_natural_disaster.md`
- `playbook_raw_material_shortage.md`
- `playbook_geopolitical_conflict.md`
- `playbook_transportation_delay.md`

All playbooks begin with `[DERIVED]` to prevent confusing statistical aggregates with individual case evidence.
