"""Retail Analytics Dashboard (Streamlit entry point).

Run with:  streamlit run app/streamlit_app.py
Reads the DuckDB file built by dbt (default data/retail.duckdb, override with DUCKDB_PATH).
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import render_sidebar_filters  # noqa: E402

st.set_page_config(page_title="Retail Analytics Dashboard", page_icon=":bar_chart:", layout="wide")

VIEWS = Path(__file__).resolve().parent / "views"
pages = [
    st.Page(VIEWS / "overview.py", title="Overview", icon=":material/dashboard:", default=True),
    st.Page(VIEWS / "sales_trends.py", title="Sales trends", icon=":material/show_chart:"),
    st.Page(VIEWS / "top_products.py", title="Top products", icon=":material/leaderboard:"),
    st.Page(VIEWS / "stockouts.py", title="Stockouts", icon=":material/inventory_2:"),
    st.Page(VIEWS / "store_comparison.py", title="Store comparison", icon=":material/store:"),
    st.Page(VIEWS / "cohorts.py", title="Cohorts", icon=":material/groups:"),
    st.Page(VIEWS / "basket_margin.py", title="Basket & margin", icon=":material/shopping_basket:"),
]
nav = st.navigation(pages)
render_sidebar_filters()
nav.run()
