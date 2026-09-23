"""Unit tests for the synthetic data generator."""

from __future__ import annotations

import json
from datetime import date

import numpy as np
import pandas as pd
import pytest

from data_gen import TABLES, generate, get_config, write_dataset
from data_gen.catalog import CATEGORY_NAMES, CHANNELS, LOYALTY_TIERS
from data_gen.generator import demand_curve


@pytest.fixture(scope="module")
def small():
    return generate(get_config("small"))


def test_deterministic_for_same_seed(small):
    again = generate(get_config("small"))
    for name in TABLES:
        pd.testing.assert_frame_equal(getattr(small, name), getattr(again, name))


def test_different_seed_changes_data(small):
    other = generate(get_config("small", seed=7))
    assert not small.order_lines.equals(other.order_lines)


def test_row_counts_and_dimensions(small):
    cfg = get_config("small")
    counts = small.row_counts()
    assert counts["stores"] == cfg.n_stores
    assert counts["products"] == cfg.n_products
    assert counts["customers"] == cfg.n_customers
    assert counts["orders"] > 1000
    assert counts["order_lines"] > counts["orders"]


def test_primary_keys_unique(small):
    assert small.stores["store_id"].is_unique
    assert small.products["product_id"].is_unique
    assert small.products["sku"].is_unique
    assert small.customers["customer_id"].is_unique
    assert small.orders["order_id"].is_unique
    assert small.order_lines["order_line_id"].is_unique
    inv_key = small.inventory_snapshots[["snapshot_date", "store_id", "product_id"]]
    assert not inv_key.duplicated().any()


def test_referential_integrity(small):
    o, lines = small.orders, small.order_lines
    assert set(lines["order_id"]) == set(o["order_id"])  # no empty orders
    assert set(lines["product_id"]) <= set(small.products["product_id"])
    assert set(o["store_id"]) <= set(small.stores["store_id"])
    assert set(o["customer_id"].dropna()) <= set(small.customers["customer_id"])
    assert set(lines["promo_id"].dropna()) <= set(small.promotions["promo_id"])


def test_accepted_values(small):
    assert set(small.products["category"]) <= set(CATEGORY_NAMES)
    assert set(small.orders["channel"]) <= set(CHANNELS)
    assert set(small.customers["loyalty_tier"]) <= set(LOYALTY_TIERS)


def test_prices_costs_and_quantities(small):
    p = small.products
    assert (p["unit_cost"] > 0).all()
    assert (p["unit_price"] > p["unit_cost"]).all()
    lines = small.order_lines
    assert (lines["quantity"] >= 1).all()
    assert lines["discount_pct"].between(0, 0.5).all()
    merged = lines.merge(p[["product_id", "unit_price"]], on="product_id", suffixes=("", "_list"))
    assert np.allclose(merged["unit_price"], merged["unit_price_list"])


def test_promotions_apply_only_inside_window(small):
    lines = small.order_lines.merge(small.orders[["order_id", "order_date"]], on="order_id")
    lines = lines.merge(small.products[["product_id", "category"]], on="product_id")
    promo = lines.dropna(subset=["promo_id"]).merge(
        small.promotions, on="promo_id", suffixes=("", "_promo")
    )
    assert len(promo) > 0
    assert (promo["order_date"] >= promo["start_date"]).all()
    assert (promo["order_date"] <= promo["end_date"]).all()
    assert (promo["category"] == promo["category_promo"]).all()
    assert np.allclose(promo["discount_pct"], promo["discount_pct_promo"])
    assert (lines.loc[lines["promo_id"].isna(), "discount_pct"] == 0).all()


def test_inventory_has_some_stockouts(small):
    inv = small.inventory_snapshots
    rate = (inv["on_hand_qty"] == 0).mean()
    assert 0.001 < rate < 0.25
    assert (inv["on_hand_qty"] >= 0).all()
    assert (inv["units_received"] > 0).any()


def test_sales_never_exceed_available_stock(small):
    """Units sold on a day <= previous close + units received that day."""
    inv = small.inventory_snapshots.sort_values(["store_id", "product_id", "snapshot_date"])
    sales = (
        small.order_lines.merge(small.orders[["order_id", "order_date", "store_id"]], on="order_id")
        .groupby(["order_date", "store_id", "product_id"], as_index=False)["quantity"].sum()
        .rename(columns={"order_date": "snapshot_date"})
    )
    df = inv.merge(sales, on=["snapshot_date", "store_id", "product_id"], how="left").fillna({"quantity": 0})
    df["prev"] = df.groupby(["store_id", "product_id"])["on_hand_qty"].shift()
    df = df.dropna(subset=["prev"])
    # conservation: prev + received - sold == close
    assert (df["prev"] + df["units_received"] - df["quantity"] == df["on_hand_qty"]).all()


def test_member_orders_and_repeat_customers(small):
    o = small.orders
    members = o["customer_id"].notna()
    assert 0.1 < members.mean() < 0.9
    per_customer = o.loc[members].groupby("customer_id").size()
    assert (per_customer >= 2).mean() > 0.2


def test_new_store_opens_mid_period(small):
    last = small.stores.iloc[-1]
    first_order = small.orders.loc[small.orders["store_id"] == last["store_id"], "order_date"].min()
    assert first_order >= last["open_date"]
    assert last["open_date"] > pd.Timestamp(get_config("small").start_date)


def test_seasonality_peaks_in_december():
    days = pd.date_range("2025-01-01", "2025-12-31")
    curve = pd.Series(demand_curve(days, days[0]), index=days)
    monthly = curve.groupby(curve.index.month).mean()
    assert monthly.idxmax() == 12
    assert monthly[12] > monthly[2] * 1.2
    # Saturdays busier than Mondays
    assert curve[curve.index.dayofweek == 5].mean() > curve[curve.index.dayofweek == 0].mean()


def test_invalid_config():
    with pytest.raises(ValueError):
        get_config("nope")
    with pytest.raises(ValueError):
        generate(get_config("small", start_date=date(2025, 1, 1), end_date=date(2025, 1, 3)))


@pytest.mark.parametrize("fmt", ["parquet", "csv"])
def test_write_dataset(tmp_path, small, fmt):
    cfg = get_config("small")
    paths = write_dataset(small, tmp_path, cfg, fmt=fmt)
    assert set(paths) == set(TABLES)
    for path in paths.values():
        assert path.exists() and path.stat().st_size > 0
    manifest = json.loads((tmp_path / "_manifest.json").read_text())
    assert manifest["synthetic"] is True
    assert manifest["row_counts"] == small.row_counts()
    assert "SYNTHETIC" in (tmp_path / "README.txt").read_text()
    if fmt == "parquet":
        back = pd.read_parquet(paths["orders"])
        assert len(back) == len(small.orders)
