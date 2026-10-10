.PHONY: setup data sample train test e2e api ui probe-models synapt-probe record-fixtures warm-cache eval clean

PYTHON ?= .venv/Scripts/python

setup:
	$(PYTHON) -m scripts.dev setup

data:
	$(PYTHON) -m scripts.dev data --source auto

sample:
	$(PYTHON) -m scripts.dev sample --size 500 --format cards

train:
	$(PYTHON) -m scripts.dev train

test:
	$(PYTHON) -m scripts.dev test

e2e:
	$(PYTHON) -m scripts.dev e2e

api:
	$(PYTHON) -m scripts.dev api

ui:
	$(PYTHON) -m scripts.dev ui

probe-models:
	$(PYTHON) -m scripts.dev probe-models

synapt-probe:
	$(PYTHON) -m scripts.dev synapt-probe

record-fixtures:
	$(PYTHON) -m scripts.dev record-fixtures

warm-cache:
	$(PYTHON) -m scripts.dev warm-cache

eval:
	$(PYTHON) -m scripts.dev eval --budget small

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]"
