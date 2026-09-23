# Retail Analytics Dashboard - common tasks.
#   make all      one-command setup: venv + deps, synthetic data, dbt build
#   make app      launch the Streamlit dashboard
# Use PRESET=small for a tiny dataset. Set VENV= (empty) to use the active Python.

VENV    ?= .venv
PRESET  ?= default
SEED    ?= 42
PYTHON_BOOT ?= python3

ifeq ($(strip $(VENV)),)
BIN :=
else
BIN := $(VENV)/bin/
endif

PY   := $(BIN)python
DBT  := $(BIN)dbt
DBT_FLAGS := --project-dir dbt --profiles-dir dbt

export DUCKDB_PATH  ?= data/retail.duckdb
export RAW_DATA_DIR ?= data/raw

.PHONY: all setup data build app test export docs clean help

help:
	@grep -E '^#   ' Makefile | sed 's/^#   //'
	@echo "  targets: setup data build app test export docs clean"

all: setup data build

$(VENV)/bin/python:
	$(PYTHON_BOOT) -m venv $(VENV)

setup: $(if $(strip $(VENV)),$(VENV)/bin/python)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt

data:
	$(PY) -m data_gen --out $(RAW_DATA_DIR) --preset $(PRESET) --seed $(SEED)

build:
	mkdir -p $(dir $(DUCKDB_PATH))
	$(DBT) build $(DBT_FLAGS)

app:
	$(BIN)streamlit run app/streamlit_app.py

test:
	$(PY) -m pytest

export:
	$(PY) scripts/export_marts.py --db $(DUCKDB_PATH) --out data/exports

docs:
	$(DBT) docs generate $(DBT_FLAGS)
	$(DBT) docs serve $(DBT_FLAGS)

clean:
	rm -rf data dbt/target dbt/logs dbt/dbt_packages logs target .pytest_cache
