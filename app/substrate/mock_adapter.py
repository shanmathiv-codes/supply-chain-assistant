"""Mock Substrate Adapter implementing all read tools on local ledger and cards."""
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.ids import generate_evidence_id
from app.schemas.evidence import Evidence


class MockSubstrateAdapter:
    """In-memory mock substrate executing against local ledger and playbooks."""

    def __init__(self, ledger_path: Path | None = None):
        self.ledger_path = ledger_path or (Path("dataset/processed/cases_clean.parquet"))
        self._df: pd.DataFrame | None = None
        self._playbooks: dict[str, str] = {}
        self._load_data()

    def _load_data(self):
        if self.ledger_path.exists():
            self._df = pd.read_parquet(self.ledger_path)
        else:
            self._df = pd.DataFrame()

        # Load playbooks
        pb_dir = Path("dataset/playbooks")
        if pb_dir.exists():
            for p in pb_dir.glob("*.md"):
                self._playbooks[p.stem] = p.read_text(encoding="utf-8")

    async def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "mode": "mock",
            "cases_loaded": len(self._df) if self._df is not None else 0,
            "playbooks_loaded": len(self._playbooks),
        }

    async def get_stats(self, provider_id: str = "") -> dict[str, Any]:
        return {
            "provider_id": provider_id or "mock-provider",
            "provider_kind": "mock",
            "total_nodes": len(self._df) * 8 if self._df is not None else 0,
            "counts_by_label": {
                "SupplyChainDisruption": len(self._df) if self._df is not None else 0,
                "DisruptionType": len(self._df["disruption_type"].unique()) if self._df is not None and "disruption_type" in self._df else 0,
                "Industry": len(self._df["industry"].unique()) if self._df is not None and "industry" in self._df else 0,
            },
            "has_ticket_store": True,
            "ticket_mining": {"accuracy": 0.88, "labels": ["disruption_type", "disruption_severity"]},
        }

    async def get_schema(self, provider_id: str = "") -> dict[str, Any]:
        return {
            "node_types": [
                "SupplyChainDisruption", "DisruptionType", "Industry",
                "SupplierTier", "SupplierRegion", "SupplierSize", "Severity", "Response", "Recovery"
            ],
            "edge_types": [
                "HAS_TYPE", "AFFECTS_INDUSTRY", "HAS_SUPPLIER_TIER",
                "HAS_SUPPLIER_REGION", "HAS_SUPPLIER_SIZE", "HAS_SEVERITY",
                "HAS_RESPONSE", "HAS_RECOVERY"
            ],
            "properties": ["disruption_id", "production_impact_pct", "revenue_loss_usd", "full_recovery_days"],
        }

    async def find_exact(self, label: str, provider_id: str = "") -> list[Evidence]:
        results = []
        if self._df is not None and not self._df.empty:
            matches = self._df[
                (self._df["disruption_id"].astype(str).str.lower() == label.lower()) |
                (self._df["disruption_type"].astype(str).str.lower() == label.lower()) |
                (self._df["industry"].astype(str).str.lower() == label.lower())
            ]
            for _, r in matches.head(5).iterrows():
                results.append(
                    Evidence(
                        evidence_id=generate_evidence_id(),
                        tool="trident_find_exact",
                        provider_id=provider_id or "mock-provider",
                        provenance_mode="MOCK",
                        case_id=r["disruption_id"],
                        node_id=f"node_{r['disruption_id']}",
                        text_span=f"Case {r['disruption_id']}: {r['disruption_type']} in {r['industry']}",
                        score=1.0,
                    )
                )
        return results

    async def search_nodes(self, query: str, top_k: int = 5, provider_id: str = "") -> list[Evidence]:
        results = []
        if self._df is not None and not self._df.empty:
            q_lower = query.lower()
            matched = self._df[
                self._df["disruption_type"].astype(str).str.lower().apply(lambda x: x in q_lower or q_lower in x) |
                self._df["industry"].astype(str).str.lower().apply(lambda x: x in q_lower or q_lower in x)
            ]
            if matched.empty:
                matched = self._df.head(top_k)
            for _, r in matched.head(top_k).iterrows():
                results.append(
                    Evidence(
                        evidence_id=generate_evidence_id(),
                        tool="trident_search",
                        provider_id=provider_id or "mock-provider",
                        provenance_mode="MOCK",
                        case_id=r["disruption_id"],
                        node_id=f"node_{r['disruption_id']}",
                        text_span=f"Node {r['disruption_id']}: {r['disruption_type']} ({r['disruption_severity']})",
                        score=0.85,
                    )
                )
        return results

    async def get_chunks(self, query: str, top_k: int = 5, provider_id: str = "") -> list[Evidence]:
        results = []
        if self._df is not None and not self._df.empty:
            # Return top_k simulated chunks matching query terms
            [t.lower() for t in query.split() if len(t) > 2]
            subset = self._df.head(top_k)
            for _, r in subset.iterrows():
                card_text = (
                    f"## Case {r['disruption_id']}\n"
                    f"disruption_type: {r['disruption_type']} | severity: {r['disruption_severity']}\n"
                    f"A {r['disruption_severity'].lower()} {r['disruption_type'].lower()} event in {r['industry']}."
                )
                results.append(
                    Evidence(
                        evidence_id=generate_evidence_id(),
                        tool="trident_get_chunks",
                        provider_id=provider_id or "mock-provider",
                        provenance_mode="MOCK",
                        case_id=r["disruption_id"],
                        chunk_id=f"chunk_{r['disruption_id']}",
                        text_span=card_text,
                        score=0.80,
                    )
                )
        return results

    async def query(self, query_text: str, top_k: int = 5, provider_id: str = "") -> dict[str, Any]:
        chunks = await self.get_chunks(query_text, top_k=top_k, provider_id=provider_id)
        cited_ids = [c.case_id for c in chunks if c.case_id]
        return {
            "answer": f"Historical disruptions associated with '{query_text}' show typical recovery times between 20-60 days.",
            "confidence": 0.78,
            "query_ref": f"qref-mock-{len(cited_ids)}",
            "cited_case_ids": cited_ids,
            "evidence": chunks,
        }

    async def label_ticket(self, ticket_text: str, provider_id: str = "") -> dict[str, Any]:
        # Return predicted label from keyword heuristic
        lower_t = ticket_text.lower()
        d_type = "Natural Disaster" if "flood" in lower_t or "storm" in lower_t else "Operational Failure"
        sev = "High" if "severe" in lower_t or "critical" in lower_t else "Medium"
        return {
            "disruption_type": d_type,
            "disruption_severity": sev,
            "confidence": 0.82,
            "exemplars": ["DIS-00001", "DIS-00002"],
        }

    async def cypher(self, template_name: str, params: dict[str, Any], provider_id: str = "") -> list[dict[str, Any]]:
        if self._df is None or self._df.empty:
            return []

        limit = params.get("limit", 20)
        exclude_case_ids = set(params.get("exclude_case_ids", []))

        if template_name == "attr_filter_all":
            filtered = self._df[~self._df["disruption_id"].isin(exclude_case_ids)]
            if params.get("disruption_type"):
                filtered = filtered[filtered["disruption_type"] == params["disruption_type"]]
            if params.get("disruption_severity"):
                filtered = filtered[filtered["disruption_severity"] == params["disruption_severity"]]
            if params.get("industry"):
                filtered = filtered[filtered["industry"] == params["industry"]]
            return filtered[["disruption_id"]].head(limit).to_dict(orient="records")

        elif template_name == "attr_overlap_rank":
            filtered = self._df[~self._df["disruption_id"].isin(exclude_case_ids)].copy()
            # Score overlap
            params.get("target_composite_keys", [])
            results = []
            for _, r in filtered.head(limit).iterrows():
                why = [f"disruption_type:{r['disruption_type']}", f"disruption_severity:{r['disruption_severity']}"]
                results.append({
                    "case_id": r["disruption_id"],
                    "disruption_id": r["disruption_id"],
                    "shared_count": len(why),
                    "why": why,
                })
            return results

        elif template_name == "outcomes_by_response":
            c_ids = params.get("case_ids", [])
            sub = self._df[self._df["disruption_id"].isin(c_ids)] if c_ids else self._df
            grouped = []
            for r_type, grp in sub.groupby("response_type"):
                grouped.append({
                    "response_type": r_type,
                    "n": len(grp),
                    "median_full_recovery": float(grp["full_recovery_days"].median()),
                    "min_full_recovery": float(grp["full_recovery_days"].min()),
                    "max_full_recovery": float(grp["full_recovery_days"].max()),
                })
            return grouped[:limit]

        elif template_name == "distinct_attribute_values":
            label = params.get("node_label", "DisruptionType")
            col = "disruption_type" if "Type" in label else "disruption_severity"
            vals = [{"value": v} for v in self._df[col].unique() if pd.notna(v)]
            return vals[:limit]

        return []

    async def get_node(self, node_id: str, depth: int = 1, provider_id: str = "") -> dict[str, Any]:
        return {
            "node_id": node_id,
            "depth": depth,
            "properties": {"disruption_id": node_id.replace("node_", "")},
            "neighbors": [],
        }

    async def traverse(self, start_node_id: str, edge_types: list[str], provider_id: str = "") -> list[dict[str, Any]]:
        return [{"from": start_node_id, "edge": edge_types[0] if edge_types else "RELATED", "to": "target_node"}]

    async def get_procedures(self, query: str, provider_id: str = "") -> list[Evidence]:
        ev_list = []
        q_lower = query.lower()
        for stem, text in self._playbooks.items():
            if any(term in stem for term in q_lower.split()):
                ev_list.append(
                    Evidence(
                        evidence_id=generate_evidence_id(),
                        tool="trident_get_procedures",
                        provider_id=provider_id or "mock-provider",
                        provenance_mode="MOCK",
                        doc_id=stem,
                        text_span=text[:500],
                        score=0.90,
                    )
                )
        if not ev_list and self._playbooks:
            # Return first playbook as default
            stem, text = next(iter(self._playbooks.items()))
            ev_list.append(
                Evidence(
                    evidence_id=generate_evidence_id(),
                    tool="trident_get_procedures",
                    provider_id=provider_id or "mock-provider",
                    provenance_mode="MOCK",
                    doc_id=stem,
                    text_span=text[:500],
                    score=0.75,
                )
            )
        return ev_list

    async def episodes(self, query: str | None = None, episode_id: str | None = None, provider_id: str = "") -> dict[str, Any]:
        return {
            "status": "healthy",
            "episodes_count": 142,
            "matching_episodes": [
                {
                    "episode_id": "EP-001",
                    "pattern": "High severity Tier 1 disruptions with no backup supplier exhibit prolonged recovery.",
                    "confidence": 0.86,
                    "recurrence_count": 14,
                }
            ],
        }
