"""Deterministic synthetic retail data generator.

Produces a small retail universe (stores, products, loyalty customers,
promotions, orders, order lines and daily inventory snapshots) with:

* annual seasonality (summer bump, Black Friday spike, December peak),
* weekday effects and gentle year-over-year growth,
* category promotions that discount prices and lift demand,
* basket affinity (products have a "companion" that is often bought with them),
* an inventory simulation with reorder points, lead times and supplier delays,
  so that stockouts happen and suppress sales.

ALL DATA IS SYNTHETIC. It does not describe any real business or person.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .catalog import (
    AGE_BANDS,
    BRANDS,
    CATEGORIES,
    CATEGORY_NAMES,
    COMPLEMENTS,
    SIZES,
    STORE_FORMATS,
    STORE_LOCATIONS,
)
from .config import GeneratorConfig

TABLES = (
    "stores",
    "products",
    "customers",
    "promotions",
    "orders",
    "order_lines",
    "inventory_snapshots",
)


@dataclass
class RetailDataset:
    stores: pd.DataFrame
    products: pd.DataFrame
    customers: pd.DataFrame
    promotions: pd.DataFrame
    orders: pd.DataFrame
    order_lines: pd.DataFrame
    inventory_snapshots: pd.DataFrame

    def tables(self) -> dict[str, pd.DataFrame]:
        return {name: getattr(self, name) for name in TABLES}

    def row_counts(self) -> dict[str, int]:
        return {name: len(df) for name, df in self.tables().items()}


# ---------------------------------------------------------------------------
# Demand shape helpers
# ---------------------------------------------------------------------------

WEEKDAY_FACTOR = np.array([0.85, 0.85, 0.90, 0.95, 1.10, 1.30, 1.05])  # Mon..Sun


def demand_curve(days: pd.DatetimeIndex, start: pd.Timestamp) -> np.ndarray:
    """Relative demand multiplier for each calendar day."""
    doy = days.dayofyear.to_numpy().astype(float)
    annual = 1.0 + 0.12 * np.cos(2 * np.pi * (doy - 196) / 365.0)  # summer bump
    december = 0.55 * np.exp(-(((doy - 354) / 12.0) ** 2))  # holiday peak
    black_friday = 0.9 * np.exp(-(((doy - 332) / 2.5) ** 2))  # late-November spike
    january_lull = -0.12 * np.exp(-(((doy - 20) / 12.0) ** 2))
    weekday = WEEKDAY_FACTOR[days.dayofweek.to_numpy()]
    growth = 1.0 + 0.08 * ((days - start).days.to_numpy() / 365.0)
    return (annual + december + black_friday + january_lull) * weekday * growth


# ---------------------------------------------------------------------------
# Dimension tables
# ---------------------------------------------------------------------------


def _make_stores(cfg: GeneratorConfig, rng: np.random.Generator, days: pd.DatetimeIndex):
    n = cfg.n_stores
    if n > len(STORE_LOCATIONS):
        raise ValueError(f"n_stores must be <= {len(STORE_LOCATIONS)}")
    formats = ["flagship"] + ["standard"] * max(0, n - 1)
    # make roughly a third of the non-flagship stores "express"
    for i in range(2, n, 3):
        formats[i] = "express"
    open_offset = np.zeros(n, dtype=int)
    if n >= 3:
        # the last store opens part-way through the period (new-store ramp)
        open_offset[-1] = int(len(days) * 0.4)
    rows = []
    for i in range(n):
        town, region = STORE_LOCATIONS[i]
        fmt = formats[i]
        lo, hi = STORE_FORMATS[fmt]["sqft"]
        opened = days[open_offset[i]] if open_offset[i] > 0 else days[0] - pd.Timedelta(
            days=int(rng.integers(365, 365 * 8))
        )
        rows.append(
            {
                "store_id": i + 1,
                "store_code": f"S{i + 1:03d}",
                "store_name": f"{town} {fmt.title()}",
                "city": town,
                "region": region,
                "store_format": fmt,
                "square_feet": int(rng.integers(lo, hi) // 100 * 100),
                "open_date": opened.normalize(),
            }
        )
    stores = pd.DataFrame(rows)
    traffic = np.array([STORE_FORMATS[f]["traffic"] for f in formats]) * rng.uniform(0.85, 1.15, n)
    return stores, traffic, open_offset


def _make_products(cfg: GeneratorConfig, rng: np.random.Generator):
    n = cfg.n_products
    cats = [CATEGORY_NAMES[i % len(CATEGORY_NAMES)] for i in range(n)]
    rows = []
    seen: set[str] = set()
    for i, cat in enumerate(cats):
        spec = CATEGORIES[cat]
        # build a unique, fictional product name
        for _ in range(50):
            brand = str(rng.choice(BRANDS))
            name = f"{brand} {rng.choice(spec['items'])} {rng.choice(SIZES)}"
            if name not in seen:
                break
        else:
            name = f"{name} #{i + 1}"
        seen.add(name)
        lo, hi = spec["price"]
        price = round(float(np.exp(rng.uniform(np.log(lo), np.log(hi)))), 2)
        margin = rng.uniform(*spec["margin"])
        cost = round(price * (1 - margin), 2)
        rows.append(
            {
                "product_id": i + 1,
                "sku": f"SKU-{i + 1:05d}",
                "product_name": name,
                "category": cat,
                "brand": brand,
                "unit_cost": cost,
                "unit_price": price,
            }
        )
    products = pd.DataFrame(rows)
    # Zipf-like popularity (shuffled so it is not tied to product_id order),
    # damped for expensive items so cheap staples sell more units.
    ranks = rng.permutation(n) + 1
    prices = products["unit_price"].to_numpy()
    popularity = (1.0 / ranks**0.8) * (prices / np.median(prices)) ** -0.7
    popularity /= popularity.sum()
    # Each product has a "companion" in a complementary category that is often
    # bought with it (e.g. pasta + sparkling water, earbuds + charger).
    cat_arr = np.array(cats)
    companion = np.empty(n, dtype=int)
    for i, cat in enumerate(cats):
        pool = np.where((cat_arr == COMPLEMENTS[cat]) & (np.arange(n) != i))[0]
        if len(pool) == 0:
            pool = np.setdiff1d(np.arange(n), [i])
        companion[i] = rng.choice(pool)
    lead_time = rng.integers(2, 7, n)
    fragile = rng.random(n) < cfg.fragile_product_share
    safety_days = np.where(fragile, rng.uniform(0.0, 1.0, n), rng.uniform(2.0, 5.0, n))
    return products, popularity, companion, lead_time, safety_days


def _make_promotions(cfg: GeneratorConfig, rng: np.random.Generator, days: pd.DatetimeIndex):
    rows = []
    promo_id = 1
    n_days = len(days)
    for cat in CATEGORY_NAMES:
        d = int(rng.integers(5, 30))
        while d < n_days:
            length = int(rng.integers(7, 15))
            end = min(d + length - 1, n_days - 1)
            rows.append(
                {
                    "promo_id": promo_id,
                    "promo_name": f"{cat} Savings Week {promo_id}",
                    "category": cat,
                    "start_date": days[d],
                    "end_date": days[end],
                    "discount_pct": round(float(rng.choice([0.10, 0.15, 0.20, 0.25, 0.30])), 2),
                    "start_idx": d,
                    "end_idx": end,
                }
            )
            promo_id += 1
            d = end + int(rng.integers(35, 70))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


def _make_customers_and_member_orders(cfg, rng, days, curve, store_traffic, open_offset):
    n_days = len(days)
    n = cfg.n_customers
    open_weight = store_traffic / store_traffic.sum()
    home_store = rng.choice(len(store_traffic), size=n, p=open_weight)

    # Acquisition day: weighted by demand curve and store open date.
    acq = np.empty(n, dtype=int)
    for s in range(len(store_traffic)):
        idx = np.where(home_store == s)[0]
        if len(idx) == 0:
            continue
        w = curve.copy()
        w[: open_offset[s]] = 0.0
        # acquisition is front-loaded a little (launch of the loyalty scheme)
        w = w * np.linspace(1.4, 0.8, n_days)
        acq[idx] = rng.choice(n_days, size=len(idx), p=w / w.sum())

    lifetime = rng.exponential(cfg.mean_customer_lifetime_days, n).astype(int) + 1
    end = np.minimum(acq + lifetime, n_days - 1)
    rate = cfg.member_order_rate * rng.lognormal(mean=-0.18, sigma=0.6, size=n)

    tier = np.select(
        [rate >= np.quantile(rate, 0.85), rate >= np.quantile(rate, 0.5)],
        ["gold", "silver"],
        default="bronze",
    )
    customers = pd.DataFrame(
        {
            "customer_id": np.arange(1, n + 1),
            "signup_date": days[acq],
            "home_store_id": home_store + 1,
            "loyalty_tier": tier,
            "age_band": rng.choice(AGE_BANDS, size=n, p=[0.1, 0.22, 0.22, 0.2, 0.15, 0.11]),
        }
    )

    # First order on acquisition day, then a thinned Poisson process.
    cmax = curve.max()
    span = np.maximum(end - acq, 0)
    n_cand = rng.poisson(rate * span * cmax / curve.mean())
    cust_idx = np.repeat(np.arange(n), n_cand)
    offs = (rng.random(len(cust_idx)) * np.repeat(span, n_cand)).astype(int) + 1
    cand_day = np.minimum(np.repeat(acq, n_cand) + offs, n_days - 1)
    keep = rng.random(len(cand_day)) < curve[cand_day] / cmax
    cust_idx = np.concatenate([np.arange(n), cust_idx[keep]])
    order_day = np.concatenate([acq, cand_day[keep]])

    # Mostly shop at the home store; sometimes elsewhere if that store is open.
    store = home_store[cust_idx].copy()
    wander = rng.random(len(store)) < 0.15
    alt = rng.choice(len(store_traffic), size=len(store), p=open_weight)
    ok = wander & (open_offset[alt] <= order_day)
    store[ok] = alt[ok]
    channel = np.where(rng.random(len(store)) < 0.12, "online", "in_store")
    member_orders = pd.DataFrame(
        {
            "day_idx": order_day,
            "store_idx": store,
            "customer_id": cust_idx + 1,
            "channel": channel,
        }
    )
    return customers, member_orders


def _make_guest_orders(cfg, rng, curve, store_traffic, open_offset):
    n_days = len(curve)
    lam = cfg.guest_orders_per_store_day * np.outer(store_traffic, curve)
    lam[np.arange(n_days)[None, :] < open_offset[:, None]] = 0.0
    counts = rng.poisson(lam)
    store_idx, day_idx = np.nonzero(counts)
    reps = counts[store_idx, day_idx]
    return pd.DataFrame(
        {
            "day_idx": np.repeat(day_idx, reps),
            "store_idx": np.repeat(store_idx, reps),
            "customer_id": pd.array([pd.NA] * int(reps.sum()), dtype="Int64"),
            "channel": np.where(rng.random(int(reps.sum())) < 0.05, "online", "in_store"),
        }
    )


def _make_lines(cfg, rng, orders, products, popularity, companion, promotions):
    n_orders = len(orders)
    n_products = len(products)
    cat_of = products["category"].to_numpy()
    qty_lambda = np.array([CATEGORIES[c]["qty_lambda"] for c in cat_of])

    n_lines = np.minimum(1 + rng.poisson(1.3, n_orders), 8)
    order_idx = np.repeat(np.arange(n_orders), n_lines)
    prod = rng.choice(n_products, size=len(order_idx), p=popularity)

    # basket affinity: companion products tag along
    tag = rng.random(len(prod)) < cfg.companion_probability
    order_idx = np.concatenate([order_idx, order_idx[tag]])
    prod = np.concatenate([prod, companion[prod[tag]]])

    # promotions lift demand: extra promoted-product lines during the window
    day_of_line = orders["day_idx"].to_numpy()[order_idx]
    extra_o, extra_p = [], []
    for promo in promotions.itertuples():
        in_window = (day_of_line >= promo.start_idx) & (day_of_line <= promo.end_idx)
        pick = in_window & (rng.random(len(prod)) < 0.06)
        if not pick.any():
            continue
        cat_products = np.where(cat_of == promo.category)[0]
        w = popularity[cat_products] / popularity[cat_products].sum()
        extra_o.append(order_idx[pick])
        extra_p.append(rng.choice(cat_products, size=int(pick.sum()), p=w))
    if extra_o:
        order_idx = np.concatenate([order_idx, *extra_o])
        prod = np.concatenate([prod, *extra_p])

    qty = 1 + rng.poisson(qty_lambda[prod])
    lines = pd.DataFrame({"order_idx": order_idx, "product_idx": prod, "quantity": qty})
    # merge duplicate products within an order
    lines = (
        lines.groupby(["order_idx", "product_idx"], as_index=False, sort=True)["quantity"].sum()
    )
    return lines


def _simulate_inventory(cfg, rng, orders, lines, n_stores, n_products, n_days,
                        open_offset, lead_time, safety_days):
    """Run a daily (s, S)-style replenishment simulation.

    Returns the mask of fulfilled lines and the daily snapshot arrays.
    """
    K = n_stores * n_products
    day = orders["day_idx"].to_numpy()[lines["order_idx"].to_numpy()]
    store = orders["store_idx"].to_numpy()[lines["order_idx"].to_numpy()]
    key = store * n_products + lines["product_idx"].to_numpy()
    qty = lines["quantity"].to_numpy()

    open_days = np.maximum(n_days - open_offset, 1)
    demand = np.bincount(key, weights=qty, minlength=K) / np.repeat(open_days, n_products)
    demand = np.maximum(demand, 0.05)
    lt = np.tile(lead_time, n_stores)
    sd = np.tile(safety_days, n_stores)
    review = 7
    rop = np.ceil(demand * (lt + sd))
    target = np.ceil(demand * (lt + sd + review)) + 1

    on_hand = np.floor(target * rng.uniform(0.6, 1.0, K)).astype(np.int64)
    on_order = np.zeros(K, dtype=np.int64)
    arrivals = np.zeros((n_days + 40, K), dtype=np.int64)
    store_open_day = np.repeat(open_offset, n_products)

    snap_on_hand = np.zeros((n_days, K), dtype=np.int64)
    snap_on_order = np.zeros((n_days, K), dtype=np.int64)
    snap_received = np.zeros((n_days, K), dtype=np.int64)
    fulfilled = np.zeros(len(qty), dtype=bool)

    # lines sorted by day, then by order (i.e. arrival order within the day)
    order_sort = np.lexsort((lines["order_idx"].to_numpy(), day))
    day_sorted = day[order_sort]
    bounds = np.searchsorted(day_sorted, np.arange(n_days + 1))

    for d in range(n_days):
        arr = arrivals[d]
        on_hand += arr
        on_order -= arr
        snap_received[d] = arr

        idx = order_sort[bounds[d]: bounds[d + 1]]
        if len(idx):
            k = key[idx]
            q = qty[idx]
            s = np.argsort(k, kind="stable")
            ks, qs = k[s], q[s]
            cum = np.cumsum(qs)
            first = np.r_[True, ks[1:] != ks[:-1]]
            group_start = np.maximum.accumulate(np.where(first, np.arange(len(ks)), 0))
            base = np.where(group_start > 0, cum[group_start - 1], 0)
            within = cum - base
            ok = within <= on_hand[ks]
            fulfilled[idx[s[ok]]] = True
            sold = np.bincount(ks[ok], weights=qs[ok], minlength=K).astype(np.int64)
            on_hand -= sold

        # reorder decisions at end of day
        position = on_hand + on_order
        need = (position <= rop) & (store_open_day <= d)
        if need.any():
            cells = np.where(need)[0]
            amount = (target[cells] - position[cells]).astype(np.int64)
            delay = np.where(
                rng.random(len(cells)) < cfg.supplier_delay_probability,
                rng.integers(7, 15, len(cells)),
                0,
            )
            eta = np.minimum(d + lt[cells] + delay, n_days + 39)
            np.add.at(arrivals, (eta, cells), amount)
            on_order[cells] += amount

        snap_on_hand[d] = on_hand
        snap_on_order[d] = on_order

    return fulfilled, snap_on_hand, snap_on_order, snap_received, store_open_day


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate(cfg: GeneratorConfig) -> RetailDataset:
    """Generate the full synthetic dataset for a config. Deterministic per seed."""
    rng = np.random.default_rng(cfg.seed)
    start = pd.Timestamp(cfg.start_date)
    days = pd.date_range(start, pd.Timestamp(cfg.end_date), freq="D")
    n_days = len(days)
    if n_days < 7:
        raise ValueError("date range must cover at least 7 days")
    curve = demand_curve(days, start)

    stores, store_traffic, open_offset = _make_stores(cfg, rng, days)
    products, popularity, companion, lead_time, safety_days = _make_products(cfg, rng)
    promotions = _make_promotions(cfg, rng, days)

    customers, member_orders = _make_customers_and_member_orders(
        cfg, rng, days, curve, store_traffic, open_offset
    )
    guest_orders = _make_guest_orders(cfg, rng, curve, store_traffic, open_offset)
    orders = pd.concat([member_orders, guest_orders], ignore_index=True)
    # timestamp within the store day (08:00-21:59)
    seconds = rng.integers(8 * 3600, 22 * 3600, len(orders))
    orders["order_ts"] = days[orders["day_idx"].to_numpy()] + pd.to_timedelta(seconds, unit="s")
    orders = orders.sort_values(["order_ts", "store_idx"], kind="stable").reset_index(drop=True)

    lines = _make_lines(cfg, rng, orders, products, popularity, companion, promotions)
    fulfilled, on_hand, on_order, received, store_open_day = _simulate_inventory(
        cfg, rng, orders, lines, cfg.n_stores, cfg.n_products, n_days,
        open_offset, lead_time, safety_days,
    )
    lines = lines[fulfilled].reset_index(drop=True)

    # drop orders whose every line was out of stock, then assign ids
    orders = orders.loc[np.unique(lines["order_idx"].to_numpy())].copy()
    orders["order_id"] = np.arange(1, len(orders) + 1)
    id_map = pd.Series(orders["order_id"].to_numpy(), index=orders.index)
    lines["order_id"] = id_map.loc[lines["order_idx"].to_numpy()].to_numpy()

    # prices and promotions
    lines["product_id"] = lines["product_idx"] + 1
    lines["unit_price"] = products["unit_price"].to_numpy()[lines["product_idx"].to_numpy()]
    line_day = orders.set_index("order_id").loc[lines["order_id"], "day_idx"].to_numpy()
    line_cat = products["category"].to_numpy()[lines["product_idx"].to_numpy()]
    promo_id = np.zeros(len(lines), dtype=np.int64)
    discount = np.zeros(len(lines))
    for promo in promotions.itertuples():
        m = (line_day >= promo.start_idx) & (line_day <= promo.end_idx) & (line_cat == promo.category)
        promo_id[m] = promo.promo_id
        discount[m] = promo.discount_pct
    lines["promo_id"] = pd.array(
        [int(p) if p > 0 else pd.NA for p in promo_id], dtype="Int64"
    )
    lines["discount_pct"] = discount
    lines = lines.sort_values(["order_id", "product_id"]).reset_index(drop=True)
    lines["line_number"] = lines.groupby("order_id").cumcount() + 1
    lines["order_line_id"] = np.arange(1, len(lines) + 1)
    order_lines = lines[
        ["order_line_id", "order_id", "line_number", "product_id", "quantity",
         "unit_price", "discount_pct", "promo_id"]
    ].copy()

    orders_out = pd.DataFrame(
        {
            "order_id": orders["order_id"].to_numpy(),
            "order_ts": orders["order_ts"].to_numpy(),
            "order_date": days[orders["day_idx"].to_numpy()],
            "store_id": orders["store_idx"].to_numpy() + 1,
            "customer_id": pd.array(orders["customer_id"].to_numpy(), dtype="Int64"),
            "channel": orders["channel"].to_numpy(),
        }
    )

    # inventory snapshots for open store/product/day cells
    K = cfg.n_stores * cfg.n_products
    dd, kk = np.nonzero(np.arange(n_days)[:, None] >= store_open_day[None, :])
    inventory = pd.DataFrame(
        {
            "snapshot_date": days[dd],
            "store_id": kk // cfg.n_products + 1,
            "product_id": kk % cfg.n_products + 1,
            "on_hand_qty": on_hand[dd, kk],
            "on_order_qty": on_order[dd, kk],
            "units_received": received[dd, kk],
        }
    )
    assert K == on_hand.shape[1]

    promotions_out = promotions.drop(columns=["start_idx", "end_idx"])

    return RetailDataset(
        stores=stores,
        products=products,
        customers=customers,
        promotions=promotions_out,
        orders=orders_out,
        order_lines=order_lines,
        inventory_snapshots=inventory,
    )
