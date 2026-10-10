MATCH (n {provider_id: $provider_id})
WHERE n.label = $test_label
OPTIONAL MATCH (c)-[r]->(n)
RETURN n.label AS label,
       labels(n) AS node_types,
       type(r) AS incoming_relationship,
       count(r) AS relationship_count
LIMIT $limit
