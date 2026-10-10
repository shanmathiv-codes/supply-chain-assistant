MATCH (n:{{node_label}} {provider_id: $provider_id})
RETURN DISTINCT n.label AS value
ORDER BY value
LIMIT $limit
