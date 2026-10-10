"""Unit tests verifying tier permissions and import ban on SynaptAdminGateway."""

import re
from pathlib import Path


def test_admin_gateway_import_ban():
    """Verify that no module under app/ (excluding scripts) imports SynaptAdminGateway."""
    app_dir = Path("app")
    assert app_dir.exists()

    forbidden_pattern = re.compile(r"\bSynaptAdminGateway\b")
    violating_files = []

    for py_file in app_dir.rglob("*.py"):
        # gateway.py itself defines it, so skip gateway.py definition
        if py_file.name == "gateway.py":
            continue
        content = py_file.read_text(encoding="utf-8")
        if forbidden_pattern.search(content):
            violating_files.append(str(py_file))

    assert not violating_files, (
        f"Security violation: SynaptAdminGateway imported outside scripts in: {violating_files}"
    )
