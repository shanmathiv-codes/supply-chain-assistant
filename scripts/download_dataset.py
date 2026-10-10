"""Dataset acquisition: checks raw CSV, tries Kaggle API, or generates synthetic fallback."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings
from data_preprocessing.synthetic.generator import save_synthetic_csv


def acquire_dataset(source: str = "auto") -> tuple[Path, str]:
    """Acquire dataset based on source strategy ('auto', 'real', 'synthetic').
    Returns: (csv_path, source_type)
    """
    raw_dir = ROOT_DIR / "dataset" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_files = list(raw_dir.glob("*.csv"))

    if source in ("auto", "real") and raw_files:
        chosen = raw_files[0]
        print(f"Acquired REAL dataset from: {chosen}")
        return chosen, "real"

    if source == "real" and not raw_files:
        raise FileNotFoundError(
            "Source mode 'real' requested, but no CSV file found in dataset/raw/."
        )

    # Check if Kaggle download is possible
    if source in ("auto", "real") and settings.kaggle_username and settings.kaggle_key:
        print("Attempting Kaggle API download...")
        try:
            import kaggle  # type: ignore

            kaggle.api.authenticate()
            kaggle.api.dataset_download_files(
                settings.dataset_kaggle_slug,
                path=str(raw_dir),
                unzip=True,
            )
            downloaded = list(raw_dir.glob("*.csv"))
            if downloaded:
                print(f"Successfully downloaded from Kaggle: {downloaded[0]}")
                return downloaded[0], "real"
        except Exception as e:
            print(f"Kaggle download failed or not configured: {e}")

    # Fallback to synthetic
    synthetic_path = ROOT_DIR / "dataset" / "synthetic" / "synthetic_cases.csv"
    if not synthetic_path.exists():
        print(f"Generating synthetic fallback dataset (3,000 rows) at: {synthetic_path}")
        save_synthetic_csv(synthetic_path, n_rows=3000, seed=42)
    else:
        print(f"Using existing synthetic dataset at: {synthetic_path}")

    return synthetic_path, "synthetic"


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "auto"
    path, stype = acquire_dataset(src)
    print(f"Dataset ready: {path} (source: {stype})")
