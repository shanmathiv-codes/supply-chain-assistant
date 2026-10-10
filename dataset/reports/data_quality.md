# Data Quality Report

- **Clean Records:** 100,000
- **Rejected Records:** 0
- **Rejection Rate:** 0.0%

## Numeric Distributions and Skewness
| Metric | Min | Median | Mean | Max | Skew |
|---|---|---|---|---|---|
| `production_impact_pct` | 1.0 | 30.1 | 31.4 | 100.0 | 0.42 |
| `revenue_loss_usd` | 10,000.0 | 875,466.2 | 2,522,811.9 | 373,130,977.5 | 10.32 |
| `response_time_days` | 1.0 | 2.0 | 4.1 | 64.0 | 2.84 |
| `full_recovery_days` | 8.0 | 61.0 | 75.8 | 798.0 | 1.78 |

## Categorical Value Counts
### disruption_type
- **Transportation Delay**: 25,118
- **Geopolitical**: 18,084
- **Labor Strike**: 15,017
- **Natural Disaster**: 15,016
- **Cyber Attack**: 14,887
- **Factory Incident**: 11,878

### industry
- **Electronics**: 29,844
- **Automotive**: 24,934
- **Consumer Goods**: 20,158
- **Pharmaceuticals**: 15,015
- **Aerospace**: 10,049

### supplier_tier
- **Tier 1**: 34,938
- **Tier 2**: 30,023
- **Tier 3**: 25,019
- **4**: 10,020

### supplier_region
- **Asia-Pacific**: 40,262
- **Europe**: 21,890
- **North America**: 19,939
- **South America**: 9,896
- **Africa/Middle East**: 8,013

### supplier_size
- **Medium**: 45,161
- **Small**: 29,872
- **Large**: 24,967

### disruption_severity
- **2**: 31,553
- **3**: 29,804
- **1**: 20,390
- **4**: 14,462
- **5**: 3,791

### response_type
- **Alternative Supplier**: 44,362
- **Production Reroute**: 18,858
- **Inventory Buffer**: 12,687
- **Customer Delay**: 12,429
- **Combined Strategy**: 11,664
