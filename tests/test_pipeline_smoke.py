"""End-to-end smoke test: generate a small dataset, run `dbt build`, check marts and the app."""

from __future__ import annotations

import glob
import os
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

from data_gen import generate, get_config, write_dataset

pytest.importorskip("dbt.cli.main")

REPO = Path(__file__).resolve().parents[1]
DBT_DIR = REPO / "dbt"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    work = tmp_path_factory.mktemp("pipeline")
    cfg = get_config("small")
    ds = generate(cfg)
    write_dataset(ds, work / "raw", cfg)
    db = work / "retail.duckdb"

    env = {
        "RAW_DATA_DIR": str(work / "raw"),
        "RAW_FORMAT": "parquet",
        "DUCKDB_PATH": str(db),
        "DBT_TARGET_PATH": str(work / "target"),
        "DBT_LOG_PATH": str(work / "logs"),
        "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
    }
    # Run dbt in a subprocess so its read-write DuckDB connection is closed afterwards.
    proc = subprocess.run(
        [sys.executable, "-m", "dbt.cli.main", "build",
         "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)],
        env={**os.environ, **env}, cwd=REPO, capture_output=True, text=True, timeout=600, check=False,
    )
    assert proc.returncode == 0, f"dbt build failed:\n{proc.stdout[-4000:]}\n{proc.stderr[-2000:]}"
    assert "ERROR=0" in proc.stdout and "WARN=0" in proc.stdout
    return {"db": db, "cfg": cfg, "ds": ds}


def count(db, table):
    with duckdb.connect(str(db), read_only=True) as con:
        return con.execute(f"select count(*) from main.{table}").fetchone()[0]


def test_dimension_row_counts(built):
    cfg, db = built["cfg"], built["db"]
    assert count(db, "dim_store") == cfg.n_stores
    assert count(db, "dim_product") == cfg.n_products
    assert count(db, "dim_customer") == cfg.n_customers
    assert count(db, "dim_date") == cfg.n_days


def test_fact_matches_raw_lines(built):
    assert count(built["db"], "fct_sales") == len(built["ds"].order_lines)


def test_mart_row_counts(built):
    db, ds = built["db"], built["ds"]
    assert count(db, "mart_inventory") == len(ds.inventory_snapshots)
    assert 0 < count(db, "mart_daily_sales") <= built["cfg"].n_days * built["cfg"].n_stores * 8
    assert count(db, "mart_margin") > 0
    assert count(db, "mart_basket") > 0
    assert count(db, "mart_cohorts") > 0
    with duckdb.connect(str(db), read_only=True) as con:
        n_cohorts = con.execute("select count(distinct cohort_month) from main.mart_cohorts").fetchone()[0]
        stockouts = con.execute("select sum(is_stockout::int) from main.mart_inventory").fetchone()[0]
    assert n_cohorts == 3  # small preset covers Jan-Mar 2025
    assert stockouts > 0


def test_revenue_reconciles(built):
    ds = built["ds"]
    lines = ds.order_lines
    expected = (lines["quantity"] * lines["unit_price"]
                - (lines["quantity"] * lines["unit_price"] * lines["discount_pct"]).round(2)).sum()
    with duckdb.connect(str(built["db"]), read_only=True) as con:
        got = float(con.execute("select sum(net_revenue) from main.mart_daily_sales").fetchone()[0])
    assert got == pytest.approx(expected, abs=1.0)


@pytest.mark.parametrize("page", sorted(glob.glob(str(REPO / "app" / "views" / "*.py"))))
def test_dashboard_pages_render(built, page, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("DUCKDB_PATH", str(built["db"]))
    at = AppTest.from_file(page, default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]


def test_dashboard_with_filters(built, monkeypatch):
    from datetime import date

    from streamlit.testing.v1 import AppTest

    from common import Filters

    monkeypatch.setenv("DUCKDB_PATH", str(built["db"]))
    at = AppTest.from_file(str(REPO / "app" / "views" / "overview.py"), default_timeout=60)
    at.session_state["filters"] = Filters(date(2025, 2, 1), date(2025, 2, 28), (1,), ("Grocery", "Beverages"))
    at.run()
    assert not at.exception
    labels = [m.label for m in at.metric]
    assert "Net revenue" in labels
    assert at.caption[0].value.startswith("01 Feb 2025 to 28 Feb 2025")  # filters were applied


def test_entrypoint_renders(built, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("DUCKDB_PATH", str(built["db"]))
    at = AppTest.from_file(str(REPO / "app" / "streamlit_app.py"), default_timeout=60).run()
    assert not at.exception
    assert at.title[0].value == "Overview"
