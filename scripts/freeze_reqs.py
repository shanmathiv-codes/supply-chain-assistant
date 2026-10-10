"""Freeze installed packages to lock files using standard library metadata."""
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent

def freeze_venv(venv_path: Path, output_file: Path):
    # site-packages path
    sp = venv_path / "Lib" / "site-packages"
    if not sp.exists():
        raise FileNotFoundError(f"Site packages not found at {sp}")

    import importlib.metadata
    # Temporarily prepend site-packages to sys.path to read distributions
    old_path = list(sys.path)
    sys.path.insert(0, str(sp))
    try:
        dists = importlib.metadata.distributions(path=[str(sp)])
        pkgs = {}
        for d in dists:
            name = d.metadata["Name"]
            ver = d.version
            pkgs[name.lower()] = f"{name}=={ver}"

        sorted_lines = [pkgs[k] for k in sorted(pkgs.keys())]
        output_file.write_text("\n".join(sorted_lines) + "\n", encoding="utf-8")
        print(f"{output_file.name} written with {len(sorted_lines)} packages.")
    finally:
        sys.path = old_path

if __name__ == "__main__":
    freeze_venv(root / ".venv", root / "requirements.lock.txt")
    freeze_venv(root / ".venv-eval", root / "requirements-eval.lock.txt")
