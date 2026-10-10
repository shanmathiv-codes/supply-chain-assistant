import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from data_preprocessing.synthetic.generator import generate_synthetic_dataset

fixture_path = Path("tests/fixtures/mini_dataset.csv")
fixture_path.parent.mkdir(parents=True, exist_ok=True)
df = generate_synthetic_dataset(n_rows=60, seed=123)
df.to_csv(fixture_path, index=False, encoding="utf-8")
print(f"Created {fixture_path} with {len(df)} rows.")
