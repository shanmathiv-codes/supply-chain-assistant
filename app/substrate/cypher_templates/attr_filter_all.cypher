MATCH (c:{{case_label}} {provider_id: $provider_id})
WHERE NOT c.label IN $exclude_case_ids
MATCH (c)-[:HAS_TYPE]->(dt:DisruptionType)
MATCH (c)-[:HAS_SEVERITY]->(sev:Severity)
MATCH (c)-[:AFFECTS_INDUSTRY]->(ind:Industry)
WHERE ($disruption_type IS NULL OR dt.label = $disruption_type)
  AND ($disruption_severity IS NULL OR sev.label = $disruption_severity)
  AND ($industry IS NULL OR ind.label = $industry)
RETURN c.label AS case_id, c.disruption_id AS disruption_id
LIMIT $limit
