"""Create repository directory skeleton and .gitkeep files."""
from pathlib import Path

dirs = [
    "config",
    "dataset/raw",
    "dataset/synthetic",
    "dataset/interim",
    "dataset/processed",
    "dataset/splits",
    "dataset/store",
    "dataset/synapt_sample",
    "dataset/case_cards",
    "dataset/playbooks",
    "dataset/evaluation",
    "dataset/reports",
    "dataset/schema_doc",
    "data_preprocessing/data_cleaning",
    "data_preprocessing/data_storing",
    "data_preprocessing/preprocessing",
    "data_preprocessing/case_cards",
    "data_preprocessing/synthetic",
    "data_preprocessing/eda",
    "ml/training",
    "ml/explain",
    "app/api",
    "app/schemas",
    "app/core",
    "app/llm/prompts",
    "app/substrate/cypher_templates",
    "app/services",
    "app/workflow/nodes",
    "app/feedback",
    "app/evaluation_hooks",
    "evaluation",
    "ui/pages",
    "ui/components",
    "scripts/smoke",
    "fixtures/synapt/real",
    "fixtures/synapt/mock",
    "artifacts",
    "docs",
    "tests/fixtures",
    "tests/unit",
    "tests/contract",
    "tests/workflow",
    "tests/api",
    "tests/data",
    "tests/guardrails",
    "tests/ml",
]

for d in dirs:
    p = Path(d)
    p.mkdir(parents=True, exist_ok=True)
    gitkeep = p / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()

# Also create empty __init__.py files in python packages
pkg_dirs = [
    "data_preprocessing",
    "data_preprocessing/data_cleaning",
    "data_preprocessing/data_storing",
    "data_preprocessing/preprocessing",
    "data_preprocessing/case_cards",
    "data_preprocessing/synthetic",
    "data_preprocessing/eda",
    "ml",
    "ml/training",
    "ml/explain",
    "app",
    "app/api",
    "app/schemas",
    "app/core",
    "app/llm",
    "app/substrate",
    "app/services",
    "app/workflow",
    "app/workflow/nodes",
    "app/feedback",
    "app/evaluation_hooks",
    "evaluation",
    "ui",
    "scripts",
    "tests",
]

for pkg in pkg_dirs:
    p = Path(pkg)
    p.mkdir(parents=True, exist_ok=True)
    init_file = p / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""Package initialization."""\n', encoding="utf-8")

print("Repository skeleton initialized successfully.")
