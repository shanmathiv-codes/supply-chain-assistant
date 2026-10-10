from pathlib import Path
sp = Path(".venv-eval/Lib/site-packages")
if sp.exists():
    items = list(sp.iterdir())
    print(f"Items in site-packages: {len(items)}")
else:
    print("site-packages does not exist yet")
