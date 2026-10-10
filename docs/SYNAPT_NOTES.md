# Synapt Integration & Schema Probe Notes

## Probe Execution
- **Timestamp:** 2026-10-10T17:36:05Z
- **Provider ID:** `supply_chain_disruption`
- **Substrate Content State:** `cases_present`
- **Reported Cases:** 100000

## Node Types and Properties
- **Node Labels:** SupplyChainDisruption, DisruptionType, Industry, SupplierTier, SupplierRegion, SupplierSize, Severity, Response, Recovery
- **Relationship Types:** HAS_TYPE, AFFECTS_INDUSTRY, HAS_SUPPLIER_TIER, HAS_SUPPLIER_REGION, HAS_SUPPLIER_SIZE, HAS_SEVERITY, HAS_RESPONSE, HAS_RECOVERY
- **Properties Found:** disruption_id, production_impact_pct, revenue_loss_usd, full_recovery_days

## Ticket Store & Episode Capabilities
- **Has Ticket Store:** True
- **Episodes Health:** healthy

## Graph Fidelity & Collision Analysis
- **Medium Severity vs Medium Size:** Evaluated via composite keys `type:label`.
- **Match Rate:** Graph nodes reflect clean ledger mapping.
