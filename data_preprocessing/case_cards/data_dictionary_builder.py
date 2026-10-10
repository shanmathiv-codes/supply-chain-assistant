"""Data dictionary generator producing dataset/schema_doc/data_dictionary.md."""

from pathlib import Path

from app.core.config import load_yaml_config

SCHEMA_CONFIG = load_yaml_config("dataset_schema.yaml")
TAXONOMY_CONFIG = load_yaml_config("taxonomy.yaml")


def build_data_dictionary(output_path: Path) -> Path:
    """Generate comprehensive schema and ontology documentation without case rows."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Supply Chain Disruption Domain Knowledge Dictionary",
        "",
        "## Overview",
        "This ontology defines the conceptual schema, attributes, relationships, and operational definitions "
        "governing supply chain disruption investigations. It provides background context for the Synapt knowledge "
        "graph substrate and operational reasoning pipelines. No individual historical case instances are recorded here.",
        "",
        "## Field Definitions and Known Temporal Information States",
        "",
    ]

    cols_spec = SCHEMA_CONFIG.get("columns", {})
    for col_name, spec in cols_spec.items():
        desc = spec.get("description", "Attribute description")
        dtype = spec.get("dtype", "string")
        known_at = spec.get("known_at", "T0")
        val_range = spec.get("range")

        tax_vals = TAXONOMY_CONFIG.get(col_name, {}).get("allowed_values")

        lines.extend(
            [
                f"### Field: `{col_name}`",
                f"- **Plain-English Definition:** {desc}.",
                f"- **Data Type:** `{dtype}`.",
                f"- **Information State:** Known at `{known_at}`.",
            ]
        )

        if tax_vals:
            lines.append(f"- **Allowed Categories:** {', '.join(tax_vals)}.")
        elif val_range:
            lines.append(f"- **Valid Value Range:** [{val_range[0]}, {val_range[1]}].")

        lines.append("")

    lines.extend(
        [
            "## Synapt Knowledge Graph Pack Mapping",
            "",
            "### Node Entity Types",
            "- `SupplyChainDisruption`: Root entity node representing an incident event.",
            "- `DisruptionType`: Root cause category of the event.",
            "- `Industry`: Specific economic vertical affected.",
            "- `SupplierTier`: Structural echelon of the impacted vendor (Tier 1, Tier 2, Tier 3).",
            "- `SupplierRegion`: Geographic territory of supplier facilities.",
            "- `SupplierSize`: Corporate scale of the supplier (Small, Medium, Large).",
            "- `Severity`: Operational severity classification (Low, Medium, High, Critical).",
            "- `Impact`: Quantitative operational impact metrics (production loss %, financial loss USD).",
            "- `Response`: Strategic mitigation intervention deployed.",
            "- `Recovery`: Operational timeline to partial and full restoration.",
            "",
            "### Knowledge Graph Relationship Edges",
            "- `(:SupplyChainDisruption)-[:HAS_TYPE]->(:DisruptionType)`",
            "- `(:SupplyChainDisruption)-[:AFFECTS_INDUSTRY]->(:Industry)`",
            "- `(:SupplyChainDisruption)-[:HAS_SUPPLIER_TIER]->(:SupplierTier)`",
            "- `(:SupplyChainDisruption)-[:HAS_SUPPLIER_REGION]->(:SupplierRegion)`",
            "- `(:SupplyChainDisruption)-[:HAS_SUPPLIER_SIZE]->(:SupplierSize)`",
            "- `(:SupplyChainDisruption)-[:HAS_SEVERITY]->(:Severity)`",
            "- `(:SupplyChainDisruption)-[:HAS_IMPACT]->(:Impact)`",
            "- `(:SupplyChainDisruption)-[:HAS_RESPONSE]->(:Response)`",
            "- `(:SupplyChainDisruption)-[:HAS_RECOVERY]->(:Recovery)`",
            "",
            "## Disambiguation and Wording Rules",
            "",
            "### Severity vs Supplier Size Collision Prevention",
            "The label 'Medium' applies to both `Severity` and `SupplierSize`. When formulating queries, "
            "reasoning about evidence, or traversing graph relationships, queries must reference composite "
            "keys: `severity:Medium` vs `supplier_size:Medium`. In text narratives, use unambiguous phrasing "
            "such as 'medium-severity event' versus 'medium-sized vendor organization'.",
            "",
            "### Fields Outside Standard Pack Edges",
            "`has_backup_supplier` and `permanent_supplier_change` are binary indicators recorded as node "
            "properties on `SupplyChainDisruption` rather than standalone graph nodes.",
            "",
            "### Associational vs Causal Phrasing",
            "All historical outcomes, recovery timelines, and response comparisons reflect associational patterns "
            "derived from past records. Never assert causal certainty (e.g., 'caused by' or 'guaranteed recovery'). "
            "Always express findings in terms of historical associations, confidence intervals, and uncertainty.",
        ]
    )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path
