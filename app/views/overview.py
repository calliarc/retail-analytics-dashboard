"""Overview: headline KPIs for the selected period vs the previous period."""

import pandas as pd
import plotly.express as px
import streamlit as st

from common import SYNTHETIC_NOTE, empty_notice, get_filters, money, number, pct, query

f = get_filters()
st.title("Overview")
st.caption(f"{f.start:%d %b %Y} to {f.end:%d %b %Y}. {SYNTHETIC_NOTE}")

span = (f.end - f.start).days + 1

KPI_SQL = """
select
    count(distinct order_id)                            as orders,
    sum(net_revenue)                                    as net_revenue,
    sum(gross_margin)                                   as gross_margin,
    sum(quantity)                                       as units,
    sum(case when is_member then net_revenue end)       as member_revenue,
    sum(discount_amount)                                as discount_amount
from main.fct_sales
where {where}
"""
where, params = f.clause(date_col="order_date")
cur = query(KPI_SQL.format(where=where), params).iloc[0]
prev_where = where.replace("order_date between ? and ?", "order_date between ?::date - ? and ?::date - ?")
prev_params = [f.start, span, f.end, span] + params[2:]
prev = query(KPI_SQL.format(where=prev_where), prev_params).iloc[0]

inv_where, inv_params = f.clause(date_col="snapshot_date")
stockout = query(
    f"select avg(case when is_stockout then 1.0 else 0 end) as r from main.mart_inventory where {inv_where}",
    inv_params,
).iloc[0]["r"]


def delta(a, b):
    if b is None or pd.isna(b) or not b:
        return None
    return f"{(float(a) / float(b) - 1) * 100:+.1f}%"


aov = cur.net_revenue / cur.orders if cur.orders else None
prev_aov = prev.net_revenue / prev.orders if prev.orders else None
gm = cur.gross_margin / cur.net_revenue if cur.net_revenue else None

c = st.columns(6)
c[0].metric("Net revenue", money(cur.net_revenue), delta(cur.net_revenue, prev.net_revenue))
c[1].metric("Orders", number(cur.orders), delta(cur.orders, prev.orders))
c[2].metric("Avg order value", money(aov), delta(aov, prev_aov) if aov else None)
c[3].metric("Gross margin", pct(gm))
c[4].metric("Units sold", number(cur.units), delta(cur.units, prev.units))
c[5].metric("Stockout rate", pct(stockout), help="Share of store x product days closing with zero stock")
st.caption("Deltas compare with the previous period of the same length.")

d_where, d_params = f.clause()
weekly = query(
    f"""
    select date_trunc('week', date_day) as week, sum(net_revenue) as net_revenue,
           sum(gross_margin) as gross_margin
    from main.mart_daily_sales where {d_where}
    group by 1 order by 1
    """,
    d_params,
)
if not empty_notice(weekly):
    left, right = st.columns([2, 1])
    fig = px.line(weekly, x="week", y=["net_revenue", "gross_margin"],
                  labels={"value": "USD", "week": "Week", "variable": ""},
                  title="Weekly net revenue and gross margin")
    left.plotly_chart(fig, width="stretch")

    by_cat = query(
        f"""
        select category, sum(net_revenue) as net_revenue
        from main.mart_daily_sales where {d_where}
        group by 1 order by 2 desc
        """,
        d_params,
    )
    fig = px.bar(by_cat, x="net_revenue", y="category", orientation="h",
                 title="Net revenue by category", labels={"net_revenue": "USD", "category": ""})
    fig.update_yaxes(autorange="reversed")
    right.plotly_chart(fig, width="stretch")

member_share = cur.member_revenue / cur.net_revenue if cur.net_revenue else None
st.markdown(
    f"Loyalty members generated **{pct(member_share)}** of net revenue. "
    f"Promotional discounts totalled **{money(cur.discount_amount)}**."
)
