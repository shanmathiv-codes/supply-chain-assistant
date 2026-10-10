MATCH (c:{{case_label}} {provider_id: $provider_id})
WHERE c.label IN $case_ids AND NOT c.label IN $exclude_case_ids
MATCH (c)-[:HAS_RESPONSE]->(resp:Response)
MATCH (c)-[:HAS_RECOVERY]->(rec:Recovery)
RETURN resp.label AS response_type,
       count(c) AS n,
       percentileDisc(rec.full_recovery_days, 0.5) AS median_full_recovery,
       min(rec.full_recovery_days) AS min_full_recovery,
       max(rec.full_recovery_days) AS max_full_recovery
ORDER BY n DESC
LIMIT $limit
