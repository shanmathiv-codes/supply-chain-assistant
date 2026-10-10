MATCH (c:{{case_label}} {provider_id: $provider_id})
WHERE NOT c.label IN $exclude_case_ids
MATCH (c)-[r]->(attr)
WHERE attr.composite_key IN $target_composite_keys
WITH c, count(attr) AS shared_count, collect(attr.composite_key) AS why
ORDER BY shared_count DESC
RETURN c.label AS case_id, c.disruption_id AS disruption_id, shared_count, why
LIMIT $limit
