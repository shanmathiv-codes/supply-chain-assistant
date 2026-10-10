"""Case resolver mapping raw graph nodes, passages, and records to disruption_id."""

import re
from typing import Any

from app.core.config import load_yaml_config

SYNAPT_CONFIG = load_yaml_config("synapt.yaml")
CASE_ID_PATTERN = re.compile(SYNAPT_CONFIG.get("case_id_pattern", r"DIS-\d{4,6}"))
HEADING_PATTERN = re.compile(r"##\s+Case\s+(DIS-\d{4,6})")


def resolve_case_id(item: Any) -> str | None:
    """Extract disruption_id from node dict, string passage, or structured record."""
    if not item:
        return None

    if isinstance(item, str):
        # 1. Check markdown heading format
        heading_match = HEADING_PATTERN.search(item)
        if heading_match:
            return heading_match.group(1)

        # 2. General regex match
        m = CASE_ID_PATTERN.search(item)
        if m:
            return m.group(0)
        return None

    if isinstance(item, dict):
        # Direct property match
        for key in ("disruption_id", "case_id", "id", "label", "name"):
            val = item.get(key)
            if val and isinstance(val, str):
                m = CASE_ID_PATTERN.search(val)
                if m:
                    return m.group(0)

        # Search in text or properties subdict
        if "properties" in item and isinstance(item["properties"], dict):
            return resolve_case_id(item["properties"])
        if "text" in item and isinstance(item["text"], str):
            return resolve_case_id(item["text"])

    return None
