"""Sales trends over time, split by category, store, region or format."""

import plotly.express as px
import streamlit as st

from common import SYNTHETIC_NOTE, empty_notice, get_filters, query

f = get_filters()
st.title("Sales trends")
st.caption(SYNTHETIC_NOTE)

c1, c2, c3 = st.columns(3)
grain = c1.radio("Granularity", ["day", "week", "month"], index=1, horizontal=True)
split = c2.selectbox("Split by", ["none", "category", "store", "region", "store format"])
measure = c3.selectbox("Measure", ["net_revenue", "gross_margin", "units", "orders"])

split_col = {
    "none": "'All'",
    "category": "s.category",
    "store": "d.store_name",
    "region": "d.region",
    "store format": "d.store_format",
}[split]

where, params = f.clause(date_col="s.date_day", store_col="s.store_id", category_col="s.category")
df = query(
    f"""
    select date_trunc('{grain}', s.date_day) as period, {split_col} as series,
           sum(s.{measure}) as value
    from main.mart_daily_sales as s
    inner join main.dim_store as d on s.store_id = d.store_id
    where {where}
    group by 1, 2 order by 1, 2
    """,
    params,
)
if measure == "orders":
    st.caption("Orders here count orders containing each category, so they overlap across categories.")

if not empty_notice(df):
    fig = px.line(df, x="period", y="value", color="series" if split != "none" else None,
                  labels={"period": "", "value": measure.replace("_", " "), "series": split},
                  title=f"{measure.replace('_', ' ').title()} by {grain}")
    st.plotly_chart(fig, width="stretch")

    left, right = st.columns(2)
    weekday = query(
        f"""
        with daily as (
            select s.date_day, sum(s.net_revenue) as net_revenue
            from main.mart_daily_sales as s where {where} group by 1
        )
        select strftime(date_day, '%a') as weekday, isodow(date_day) as dow,
               avg(net_revenue) as avg_net_revenue
        from daily group by 1, 2 order by 2
        """,
        params,
    )
    fig = px.bar(weekday, x="weekday", y="avg_net_revenue", title="Average daily net revenue by weekday",
                 labels={"avg_net_revenue": "USD", "weekday": ""})
    left.plotly_chart(fig, width="stretch")

    promo = query(
        f"""
        select date_trunc('week', s.date_day) as week,
               sum(s.promo_net_revenue) / nullif(sum(s.net_revenue), 0) as promo_share,
               sum(s.discount_amount) / nullif(sum(s.gross_revenue), 0) as discount_rate
        from main.mart_daily_sales as s where {where} group by 1 order by 1
        """,
        params,
    )
    fig = px.line(promo, x="week", y=["promo_share", "discount_rate"],
                  title="Promotion share of revenue and discount rate (weekly)",
                  labels={"value": "", "week": "", "variable": ""})
    fig.update_yaxes(tickformat=".0%")
    right.plotly_chart(fig, width="stretch")
