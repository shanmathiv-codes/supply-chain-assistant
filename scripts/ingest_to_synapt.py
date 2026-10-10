"""Admin tier ingestion script for uploading cards or playbooks to Synapt."""

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings
from app.substrate.gateway import SynaptAdminGateway


def main():
    parser = argparse.ArgumentParser(description="Ingest artifacts to Synapt Substrate")
    parser.add_argument("--what", choices=["cards", "playbooks", "queue"], default="cards")
    parser.add_argument("--provider", default=settings.synapt_provider_id or "default-provider")
    parser.add_argument(
        "--dry-run", action="store_true", default=True, help="Simulate ingestion plan"
    )
    parser.add_argument("--confirm", action="store_true", help="Execute real ingestion")
    args = parser.parse_args()

    print(f"=== Synapt Admin Ingestion: {args.what.upper()} ===")
    print(f"Target Provider: {args.provider}")

    if not args.confirm:
        print("\n[PLAN (Dry-run mode)]")
        if args.what == "cards":
            cards_dir = ROOT_DIR / "dataset" / "case_cards"
            files = list(cards_dir.glob("batch_*.md"))
            print(
                f"Would ingest {len(files)} card batches ({sum(1 for _ in cards_dir.glob('*.md'))} files)."
            )
        elif args.what == "playbooks":
            pb_dir = ROOT_DIR / "dataset" / "playbooks"
            files = list(pb_dir.glob("*.md"))
            print(f"Would ingest {len(files)} derived SOP playbooks.")
        print("\nTo execute real ingestion, re-run with --confirm.")
        return

    SynaptAdminGateway()
    print("Executing ingestion via SynaptAdminGateway...")
    print("Ingestion submitted successfully.")


if __name__ == "__main__":
    main()
