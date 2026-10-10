# Supply Chain Disruption Domain Knowledge Dictionary

## Overview
This ontology defines the conceptual schema, attributes, relationships, and operational definitions governing supply chain disruption investigations. It provides background context for the Synapt knowledge graph substrate and operational reasoning pipelines. No individual historical case instances are recorded here.

## Field Definitions and Known Temporal Information States

### Field: `disruption_id`
- **Plain-English Definition:** Unique disruption identifier.
- **Data Type:** `string`.
- **Information State:** Known at `T0`.

### Field: `disruption_type`
- **Plain-English Definition:** Classification of disruption event.
- **Data Type:** `string`.
- **Information State:** Known at `T0`.
- **Allowed Categories:** Natural Disaster, Supplier Bankruptcy, Operational Failure, Labor Strike, Transportation Delay, Cyber Incident, Quality Issue, Geopolitical.

### Field: `industry`
- **Plain-English Definition:** Industry vertical affected.
- **Data Type:** `string`.
- **Information State:** Known at `T0`.
- **Allowed Categories:** Automotive, Electronics, Pharmaceuticals, Aerospace, Consumer Goods, Energy, Chemicals, Industrial.

### Field: `supplier_tier`
- **Plain-English Definition:** Supply chain tier (Tier 1, Tier 2, Tier 3).
- **Data Type:** `string`.
- **Information State:** Known at `T0`.
- **Allowed Categories:** Tier 1, Tier 2, Tier 3.

### Field: `supplier_region`
- **Plain-English Definition:** Geographic region of supplier.
- **Data Type:** `string`.
- **Information State:** Known at `T0`.
- **Allowed Categories:** North America, Europe, Asia-Pacific, Latin America, Middle East & Africa.

### Field: `supplier_size`
- **Plain-English Definition:** Supplier company scale (Small, Medium, Large).
- **Data Type:** `string`.
- **Information State:** Known at `T0`.
- **Allowed Categories:** Small, Medium, Large.

### Field: `has_backup_supplier`
- **Plain-English Definition:** Whether an alternate supplier contract exists.
- **Data Type:** `boolean`.
- **Information State:** Known at `T0`.

### Field: `disruption_severity`
- **Plain-English Definition:** Disruption severity rating (Low, Medium, High, Critical).
- **Data Type:** `string`.
- **Information State:** Known at `T0`.
- **Allowed Categories:** Low, Medium, High, Critical.

### Field: `production_impact_pct`
- **Plain-English Definition:** Observed percentage loss of production capacity.
- **Data Type:** `float`.
- **Information State:** Known at `T1`.
- **Valid Value Range:** [0.0, 100.0].

### Field: `revenue_loss_usd`
- **Plain-English Definition:** Direct revenue loss in USD.
- **Data Type:** `float`.
- **Information State:** Known at `T1`.
- **Valid Value Range:** [0.0, 1000000000.0].

### Field: `response_type`
- **Plain-English Definition:** Operational response strategy executed.
- **Data Type:** `string`.
- **Information State:** Known at `T2`.
- **Allowed Categories:** Reroute Shipments, Activate Backup Supplier, Expedite Freight, Buffer Inventory, Production Rescheduling, Renegotiate Contract, Accept Delay.

### Field: `response_time_days`
- **Plain-English Definition:** Elapsed days before executing response.
- **Data Type:** `float`.
- **Information State:** Known at `T2`.
- **Valid Value Range:** [0.0, 365.0].

### Field: `partial_recovery_days`
- **Plain-English Definition:** Days to resume partial operations.
- **Data Type:** `float`.
- **Information State:** Known at `outcome`.
- **Valid Value Range:** [0.0, 730.0].

### Field: `full_recovery_days`
- **Plain-English Definition:** Days to return to 100% baseline operations.
- **Data Type:** `float`.
- **Information State:** Known at `outcome`.
- **Valid Value Range:** [0.0, 1095.0].

### Field: `permanent_supplier_change`
- **Plain-English Definition:** Whether the disruption led to permanent supplier replacement.
- **Data Type:** `boolean`.
- **Information State:** Known at `outcome`.

## Synapt Knowledge Graph Pack Mapping

### Node Entity Types
- `SupplyChainDisruption`: Root entity node representing an incident event.
- `DisruptionType`: Root cause category of the event.
- `Industry`: Specific economic vertical affected.
- `SupplierTier`: Structural echelon of the impacted vendor (Tier 1, Tier 2, Tier 3).
- `SupplierRegion`: Geographic territory of supplier facilities.
- `SupplierSize`: Corporate scale of the supplier (Small, Medium, Large).
- `Severity`: Operational severity classification (Low, Medium, High, Critical).
- `Impact`: Quantitative operational impact metrics (production loss %, financial loss USD).
- `Response`: Strategic mitigation intervention deployed.
- `Recovery`: Operational timeline to partial and full restoration.

### Knowledge Graph Relationship Edges
- `(:SupplyChainDisruption)-[:HAS_TYPE]->(:DisruptionType)`
- `(:SupplyChainDisruption)-[:AFFECTS_INDUSTRY]->(:Industry)`
- `(:SupplyChainDisruption)-[:HAS_SUPPLIER_TIER]->(:SupplierTier)`
- `(:SupplyChainDisruption)-[:HAS_SUPPLIER_REGION]->(:SupplierRegion)`
- `(:SupplyChainDisruption)-[:HAS_SUPPLIER_SIZE]->(:SupplierSize)`
- `(:SupplyChainDisruption)-[:HAS_SEVERITY]->(:Severity)`
- `(:SupplyChainDisruption)-[:HAS_IMPACT]->(:Impact)`
- `(:SupplyChainDisruption)-[:HAS_RESPONSE]->(:Response)`
- `(:SupplyChainDisruption)-[:HAS_RECOVERY]->(:Recovery)`

## Disambiguation and Wording Rules

### Severity vs Supplier Size Collision Prevention
The label 'Medium' applies to both `Severity` and `SupplierSize`. When formulating queries, reasoning about evidence, or traversing graph relationships, queries must reference composite keys: `severity:Medium` vs `supplier_size:Medium`. In text narratives, use unambiguous phrasing such as 'medium-severity event' versus 'medium-sized vendor organization'.

### Fields Outside Standard Pack Edges
`has_backup_supplier` and `permanent_supplier_change` are binary indicators recorded as node properties on `SupplyChainDisruption` rather than standalone graph nodes.

### Associational vs Causal Phrasing
All historical outcomes, recovery timelines, and response comparisons reflect associational patterns derived from past records. Never assert causal certainty (e.g., 'caused by' or 'guaranteed recovery'). Always express findings in terms of historical associations, confidence intervals, and uncertainty.
