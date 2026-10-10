"""Dataset manifest generator tracking hashes, counts, source, and timestamps."""

import hashlib
import json
import time
from pathlib import Path


def calculate_file_sha256(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file."""
    if not file_path.exists():
        return ""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def update_manifest(
    manifest_path: Path,
    source: str,
    raw_path: Path,
    clean_path: Path,
    row_count: int,
    column_list: list[str],
    extra_artifacts: dict[str, str] | None = None,
) -> dict:
    """Update and write dataset/MANIFEST.json."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    artifacts = extra_artifacts or {}
    artifacts["raw_dataset"] = calculate_file_sha256(raw_path)
    artifacts["clean_ledger"] = calculate_file_sha256(clean_path)

    manifest_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": source,
        "row_count": row_count,
        "column_count": len(column_list),
        "columns": column_list,
        "sha256_checksums": artifacts,
    }

    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    return manifest_data
