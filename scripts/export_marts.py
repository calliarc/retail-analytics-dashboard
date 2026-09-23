"""Export dbt marts from DuckDB to Parquet files (for Power BI or other tools).

Usage: python scripts/export_marts.py [--db data/retail.duckdb] [--out data/exports]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

TABLES = [
    "dim_date", "dim_store", "dim_product", "dim_customer", "fct_sales",
    "mart_daily_sales", "mart_margin", "mart_basket", "mart_inventory", "mart_cohorts",
]


def export(db: str, out: str) -> list[Path]:
    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    with duckdb.connect(db, read_only=True) as con:
        for t in TABLES:
            path = out_dir / f"{t}.parquet"
            con.execute(f"copy main.{t} to '{path.as_posix()}' (format parquet)")
            written.append(path)
    return written


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", default="data/retail.duckdb")
    p.add_argument("--out", default="data/exports")
    a = p.parse_args()
    for path in export(a.db, a.out):
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
