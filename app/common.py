"""Shared helpers for the Streamlit dashboard: DuckDB access, filters, formatting."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_NOTE = "All figures are generated from **synthetic** sample data."


def db_path() -> str:
    """DuckDB file built by `make build` (override with DUCKDB_PATH)."""
    p = Path(os.environ.get("DUCKDB_PATH", "data/retail.duckdb"))
    if not p.is_absolute() and not p.exists():
        p = REPO_ROOT / p
    return str(p)


@st.cache_resource(show_spinner=False)
def _connection(path: str) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(path, read_only=True)


def _require_db() -> str:
    path = db_path()
    if not Path(path).exists():
        st.error(
            f"DuckDB file not found at `{path}`.\n\n"
            "Run `make data build` (or `make all`) first, or set `DUCKDB_PATH`."
        )
        st.stop()
    return path


@st.cache_data(show_spinner=False, ttl=600)
def _cached_query(path: str, sql: str, params: tuple) -> pd.DataFrame:
    args = [list(p) if isinstance(p, tuple) else p for p in params]
    return _connection(path).cursor().execute(sql, args).df()


def query(sql: str, params: list | tuple = ()) -> pd.DataFrame:
    """Run a read-only query against the marts. Lists in params become DuckDB lists."""
    path = _require_db()
    frozen = tuple(tuple(p) if isinstance(p, list) else p for p in params)
    return _cached_query(path, sql, frozen)


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Filters:
    start: date
    end: date
    store_ids: tuple[int, ...]
    categories: tuple[str, ...]

    def clause(
        self,
        date_col: str | None = "date_day",
        store_col: str | None = "store_id",
        category_col: str | None = "category",
    ) -> tuple[str, list]:
        """SQL WHERE fragment (without 'where') plus parameters."""
        parts, params = ["1 = 1"], []
        if date_col:
            parts.append(f"{date_col} between ? and ?")
            params += [self.start, self.end]
        if store_col:
            parts.append(f"list_contains(?, {store_col})")
            params.append(list(self.store_ids))
        if category_col:
            parts.append(f"list_contains(?, {category_col})")
            params.append(list(self.categories))
        return " and ".join(parts), params


@st.cache_data(show_spinner=False, ttl=600)
def filter_options(path: str) -> dict:
    con = _connection(path).cursor()
    lo, hi = con.execute("select min(date_day), max(date_day) from main.mart_daily_sales").fetchone()
    stores = con.execute(
        "select store_id, store_name from main.dim_store order by store_id"
    ).df()
    cats = con.execute(
        "select distinct category from main.dim_product order by category"
    ).df()["category"].tolist()
    return {"min_date": lo, "max_date": hi, "stores": stores, "categories": cats}


def default_filters() -> Filters:
    opts = filter_options(_require_db())
    return Filters(
        start=opts["min_date"],
        end=opts["max_date"],
        store_ids=tuple(int(s) for s in opts["stores"]["store_id"]),
        categories=tuple(opts["categories"]),
    )


def render_sidebar_filters() -> Filters:
    """Draw the global filters in the sidebar and store them in session state."""
    opts = filter_options(_require_db())
    stores = opts["stores"]
    names = dict(zip(stores["store_id"].astype(int), stores["store_name"], strict=True))

    with st.sidebar:
        st.header("Filters")
        picked = st.date_input(
            "Date range",
            value=(opts["min_date"], opts["max_date"]),
            min_value=opts["min_date"],
            max_value=opts["max_date"],
            key="f_dates",
        )
        store_sel = st.multiselect(
            "Stores", options=list(names), format_func=names.get, key="f_stores",
            placeholder="All stores",
        )
        cat_sel = st.multiselect(
            "Categories", options=opts["categories"], key="f_categories",
            placeholder="All categories",
        )
        st.caption(SYNTHETIC_NOTE)

    if isinstance(picked, (tuple, list)) and len(picked) == 2:
        start, end = picked
    else:  # user has clicked only the first date so far
        start = picked[0] if isinstance(picked, (tuple, list)) and picked else opts["min_date"]
        end = opts["max_date"]
    f = Filters(
        start=start,
        end=end,
        store_ids=tuple(store_sel) or tuple(names),
        categories=tuple(cat_sel) or tuple(opts["categories"]),
    )
    st.session_state["filters"] = f
    return f


def get_filters() -> Filters:
    f = st.session_state.get("filters")
    return f if isinstance(f, Filters) else default_filters()


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def money(x) -> str:
    if x is None or pd.isna(x):
        return "-"
    x = float(x)
    if abs(x) >= 1e6:
        return f"${x / 1e6:,.2f}M"
    if abs(x) >= 1e3:
        return f"${x / 1e3:,.1f}K"
    return f"${x:,.2f}"


def pct(x, digits: int = 1) -> str:
    if x is None or pd.isna(x):
        return "-"
    return f"{float(x) * 100:.{digits}f}%"


def number(x) -> str:
    if x is None or pd.isna(x):
        return "-"
    return f"{float(x):,.0f}"


def empty_notice(df: pd.DataFrame) -> bool:
    """Show an info box and return True when a result is empty."""
    if df.empty:
        st.info("No data for the current filters.")
        return True
    return False
