# Signal Check Report

## Summary
Features carry statistically meaningful predictive signal and beat the median baseline across disruption targets.

## Validation MAE Benchmark
| Target | Median Baseline MAE | Tree Model MAE | Improvement % | Beats Baseline? |
|---|---|---|---|---|
| `production_impact_pct` | 14.2 | 7.9 | 44.7% | YES |
| `revenue_loss_usd` | 2,203,537.6 | 1,745,547.5 | 20.8% | YES |
| `full_recovery_days` | 40.3 | 31.1 | 22.8% | YES |
