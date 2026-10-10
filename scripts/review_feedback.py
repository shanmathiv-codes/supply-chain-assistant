"""CLI tool for human review of user feedback and operational outcomes.

Usage:
  python -m scripts.review_feedback list
  python -m scripts.review_feedback approve --id <queue_id>
  python -m scripts.review_feedback reject --id <queue_id> --notes <reason>
  python -m scripts.review_feedback seed
"""

from __future__ import annotations

import argparse
import sys

from app.feedback.store import FeedbackStore


def cmd_list(store: FeedbackStore) -> None:
    pending = store.list_pending()
    if not pending:
        print("No pending feedback or outcome items in review queue.")
        return

    print(f"\n--- Pending Review Queue ({len(pending)} items) ---")
    for item in pending:
        qid = item["queue_id"]
        itype = item["item_type"]
        if itype == "feedback":
            print(
                f"[{qid}] FEEDBACK | Run: {item['f_run_id']} | Kind: {item['kind']} | "
                f"Value: {item['value']} | Comment: {item['comment'] or 'N/A'}"
            )
        else:
            sim = "[SIMULATED] " if item["simulated"] else ""
            print(
                f"[{qid}] OUTCOME {sim}| Run: {item['o_run_id']} | Impact: {item['actual_production_impact_pct']}% | "
                f"Loss: ${item['actual_revenue_loss_usd']} | Recovery: {item['actual_full_recovery_days']} days"
            )


def cmd_approve(store: FeedbackStore, queue_id: int, notes: str | None) -> None:
    ok = store.review_item(queue_id, "approve", notes)
    if ok:
        print(f"Successfully APPROVED queue item #{queue_id}")
    else:
        print(f"Error: Queue item #{queue_id} not found", file=sys.stderr)
        sys.exit(1)


def cmd_reject(store: FeedbackStore, queue_id: int, notes: str | None) -> None:
    ok = store.review_item(queue_id, "reject", notes)
    if ok:
        print(f"Successfully REJECTED queue item #{queue_id}")
    else:
        print(f"Error: Queue item #{queue_id} not found", file=sys.stderr)
        sys.exit(1)


def cmd_seed(store: FeedbackStore) -> None:
    f_id = store.record_feedback(
        run_id="RUN-DEMO-001",
        kind="relevance",
        value=5.0,
        comment="Analog cases closely matched our Tier-1 APAC supplier issue.",
    )
    o_id = store.record_outcome(
        run_id="RUN-DEMO-001",
        actual_production_impact_pct=22.5,
        actual_revenue_loss_usd=450000.0,
        actual_full_recovery_days=28.0,
        actual_response_type="Dual Sourcing",
        simulated=False,
    )
    print(f"Seeded feedback item #{f_id} and outcome item #{o_id} into review queue.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Human Feedback Review CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # list
    subparsers.add_parser("list", help="List all pending items in queue")

    # approve
    p_app = subparsers.add_parser("approve", help="Approve an item")
    p_app.add_argument("--id", type=int, required=True, help="Queue ID")
    p_app.add_argument("--notes", type=str, default=None, help="Reviewer notes")

    # reject
    p_rej = subparsers.add_parser("reject", help="Reject an item")
    p_rej.add_argument("--id", type=int, required=True, help="Queue ID")
    p_rej.add_argument("--notes", type=str, required=True, help="Rejection reason")

    # seed
    subparsers.add_parser("seed", help="Seed sample pending feedback items")

    args = parser.parse_args()
    store = FeedbackStore()

    if args.subcommand == "list":
        cmd_list(store)
    elif args.subcommand == "approve":
        cmd_approve(store, args.id, args.notes)
    elif args.subcommand == "reject":
        cmd_reject(store, args.id, args.notes)
    elif args.subcommand == "seed":
        cmd_seed(store)


if __name__ == "__main__":
    main()
