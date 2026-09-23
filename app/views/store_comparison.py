"""Side-by-side store performance."""

import plotly.express as px
import streamlit as st

from common import SYNTHETIC_NOTE, empty_notice, get_filters, query

f = get_filters()
st.title("Store comparison")
st.caption(SYNTHETIC_NOTE)

where, params = f.clause(date_col="s.order_date", store_col="s.store_id", category_col="s.category")
inv_where, inv_params = f.clause(date_col="i.snapshot_date", store_col="i.store_id", category_col="i.category")

df = query(
    f"""
    with sales as (
        select s.store_id,
               count(distinct s.order_id)   as orders,
               sum(s.net_revenue)           as net_revenue,
               sum(s.gross_margin)          as gross_margin,
               sum(s.quantity)              as units,
               sum(case when s.is_member then s.net_revenue else 0 end) as member_revenue,
               count(distinct s.order_date) as trading_days
        from main.fct_sales as s where {where} group by 1
    ),
    inv as (
        select i.store_id, avg(case when i.is_stockout then 1.0 else 0 end) as stockout_rate
        from main.mart_inventory as i where {inv_where} group by 1
    )
    select d.store_name, d.region, d.store_format, d.square_feet,
           s.orders, s.net_revenue, s.gross_margin, s.units,
           s.net_revenue / nullif(s.orders, 0)         as avg_order_value,
           s.gross_margin / nullif(s.net_revenue, 0)   as gross_margin_pct,
           s.member_revenue / nullif(s.net_revenue, 0) as member_share,
           s.net_revenue / nullif(s.trading_days, 0)   as revenue_per_day,
           s.net_revenue / nullif(s.trading_days, 0) * 365 / d.square_feet as annualised_revenue_per_sqft,
           i.stockout_rate
    from sales as s
    inner join main.dim_store as d on s.store_id = d.store_id
    left join inv as i on s.store_id = i.store_id
    order by s.net_revenue desc
    """,
    params + inv_params,
)

if not empty_notice(df):
    metric = st.selectbox(
        "Compare on",
        ["net_revenue", "revenue_per_day", "annualised_revenue_per_sqft", "avg_order_value",
         "gross_margin_pct", "member_share", "stockout_rate", "orders"],
        format_func=lambda m: m.replace("_", " "),
    )
    fig = px.bar(df.sort_values(metric, ascending=False), x="store_name", y=metric, color="store_format",
                 labels={"store_name": "", metric: metric.replace("_", " ")})
    if metric.endswith(("pct", "share", "rate")):
        fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, width="stretch")

    st.dataframe(
        df, hide_index=True, width="stretch",
        column_config={
            "net_revenue": st.column_config.NumberColumn("Net revenue", format="$%.0f"),
            "gross_margin": st.column_config.NumberColumn("Gross margin", format="$%.0f"),
            "avg_order_value": st.column_config.NumberColumn("AOV", format="$%.2f"),
            "gross_margin_pct": st.column_config.NumberColumn("Margin %", format="percent"),
            "member_share": st.column_config.NumberColumn("Member share", format="percent"),
            "revenue_per_day": st.column_config.NumberColumn("Revenue / day", format="$%.0f"),
            "annualised_revenue_per_sqft": st.column_config.NumberColumn("Revenue / sq ft / yr", format="$%.2f"),
            "stockout_rate": st.column_config.NumberColumn("Stockout rate", format="percent"),
        },
    )

    monthly = query(
        f"""
        select date_trunc('month', s.order_date) as month, d.store_name, sum(s.net_revenue) as net_revenue
        from main.fct_sales as s inner join main.dim_store as d on s.store_id = d.store_id
        where {where} group by 1, 2 order by 1, 2
        """,
        params,
    )
    fig = px.line(monthly, x="month", y="net_revenue", color="store_name",
                  title="Monthly net revenue by store", labels={"net_revenue": "USD", "month": "", "store_name": ""})
    st.plotly_chart(fig, width="stretch")
