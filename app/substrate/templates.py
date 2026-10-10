"""Cypher template loader, identifier validator, and query renderer."""

import re
from pathlib import Path
from typing import Any

from app.core.config import load_yaml_config

TEMPLATES_DIR = Path(__file__).resolve().parent / "cypher_templates"
SCHEMA_CONFIG = load_yaml_config("synapt_schema.yaml")
IDENTIFIER_REGEX = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_identifier(ident: str) -> str:
    """Ensure identifier matches safe alphanumeric Cypher token regex."""
    if not IDENTIFIER_REGEX.match(ident):
        raise ValueError(f"Unsafe or invalid Cypher identifier token: '{ident}'")
    return ident


def render_cypher_template(
    template_name: str,
    params: dict[str, Any] | None = None,
    placeholders: dict[str, str] | None = None,
    provider_id: str = "",
    limit: int = 20,
    exclude_case_ids: list[str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Load, validate, and render a parameterized Cypher query template.
    Returns: (rendered_cypher, bound_parameters)
    """
    t_file = TEMPLATES_DIR / f"{template_name}.cypher"
    if not t_file.exists():
        raise FileNotFoundError(f"Cypher template '{template_name}' not found at {t_file}")

    raw_query = t_file.read_text(encoding="utf-8")

    # Resolve safe structural placeholders
    sub_placeholders = {
        "case_label": validate_identifier(
            SCHEMA_CONFIG.get("node_labels", {}).get("case", "SupplyChainDisruption")
        ),
    }
    if placeholders:
        for k, v in placeholders.items():
            sub_placeholders[k] = validate_identifier(v)

    rendered = raw_query
    for ph_key, ph_val in sub_placeholders.items():
        rendered = rendered.replace(f"{{{{{ph_key}}}}}", ph_val)

    # Bind parameters safely
    bound_params: dict[str, Any] = {
        "provider_id": provider_id,
        "limit": int(limit),
        "exclude_case_ids": list(exclude_case_ids or []),
    }
    if params:
        bound_params.update(params)

    return rendered, bound_params
