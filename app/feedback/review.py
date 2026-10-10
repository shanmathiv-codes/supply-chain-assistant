"""Feedback review and case card staging module.

Processes approved operational outcomes into case cards formatted for ingestion.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.feedback.store import FeedbackStore

logger = logging.getLogger("app.feedback.review")


def review_pending_item(
    store: FeedbackStore,
    queue_id: int,
    action: str,
    reviewer_notes: str | None = None,
) -> bool:
    """Approve or reject a pending item in the queue."""
    return store.review_item(queue_id, action, reviewer_notes)


def format_outcome_as_case_card(
    case_id: str,
    outcome: dict[str, Any],
    profile: dict[str, Any],
) -> str:
    """Format an approved actual outcome into a standardized case card markdown string."""
    d_type = profile.get("disruption_type", "Unknown")
    ind = profile.get("industry", "Unknown")
    tier = profile.get("supplier_tier", "Unknown")
    reg = profile.get("supplier_region", "Unknown")
    size = profile.get("supplier_size", "Unknown")
    backup = profile.get("has_backup_supplier", "No")
    sev = profile.get("disruption_severity", "Medium")

    impact = outcome.get("actual_production_impact_pct", 0.0)
    loss = outcome.get("actual_revenue_loss_usd", 0.0)
    resp_type = outcome.get("actual_response_type", "Expedited Freight")
    resp_time = outcome.get("response_time_days", 5.0)
    part_rec = outcome.get("partial_recovery_days", 14.0)
    full_rec = outcome.get("actual_full_recovery_days", 30.0)
    perm_change = outcome.get("permanent_supplier_change", "No")

    narrative = (
        f"Operational outcome logged from incident {case_id}. "
        f"A {sev.lower()}-severity {d_type} affected a {size.lower()} {tier} supplier in {reg} for {ind}. "
        f"Response executed: {resp_type}, resulting in full recovery in {full_rec} days."
    )

    card = (
        f"## Case {case_id}\n"
        f"disruption_id: {case_id} | disruption_type: {d_type} | industry: {ind} | "
        f"supplier_tier: {tier} | supplier_region: {reg} | supplier_size: {size} | "
        f"has_backup_supplier: {backup} | disruption_severity: {sev}\n"
        f"production_impact_pct: {impact} | revenue_loss_usd: {loss} | response_type: {resp_type} | "
        f"response_time_days: {resp_time} | partial_recovery_days: {part_rec} | "
        f"full_recovery_days: {full_rec} | permanent_supplier_change: {perm_change}\n\n"
        f"{narrative}\n"
    )
    return card


def stage_approved_outcomes_for_ingestion(
    store: FeedbackStore,
    staging_dir: Path | None = None,
) -> list[Path]:
    """Export all approved outcomes into markdown cards staged for ingestion."""
    if staging_dir is None:
        staging_dir = Path("dataset/case_cards/feedback_approved")
    staging_dir.mkdir(parents=True, exist_ok=True)

    approved = store.get_approved_outcomes()
    staged_files: list[Path] = []

    for idx, item in enumerate(approved, 1):
        case_id = f"FB-CASE-{idx:04d}"
        profile = {
            "disruption_type": "Supply Shortage",
            "industry": "Manufacturing",
            "supplier_tier": "Tier 1",
            "supplier_region": "North America",
            "supplier_size": "Large",
            "has_backup_supplier": "Yes",
            "disruption_severity": "Medium",
        }
        card_content = format_outcome_as_case_card(case_id, item, profile)
        card_path = staging_dir / f"{case_id}.md"
        with open(card_path, "w", encoding="utf-8") as f:
            f.write(card_content)
        staged_files.append(card_path)

    logger.info("Staged %d approved case cards to %s", len(staged_files), staging_dir)
    return staged_files
