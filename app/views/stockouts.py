"""Stockouts and days of cover."""

import plotly.express as px
import streamlit as st

from common import SYNTHETIC_NOTE, empty_notice, get_filters, number, pct, query

f = get_filters()
st.title("Stockouts")
st.caption(
    "A stockout day is a store x product day that closed with zero units on hand. "
    "Days of cover = on-hand units / trailing 28-day average daily units sold. " + SYNTHETIC_NOTE
)

where, params = f.clause(date_col="i.snapshot_date", store_col="i.store_id", category_col="i.category")

kpi = query(
    f"""
    select count(*) as cell_days,
           sum(case when is_stockout then 1 else 0 end) as stockout_days,
           avg(case when is_stockout then 1.0 else 0 end) as stockout_rate,
           count(distinct case when is_stockout then store_id || '-' || product_id end) as skus_affected
    from main.mart_inventory as i where {where}
    """,
    params,
).iloc[0]

latest = query(
    f"""
    select i.snapshot_date, d.store_name, p.product_name, p.category, i.on_hand_qty, i.on_order_qty,
           i.avg_daily_units_trailing, i.days_of_cover
    from main.mart_inventory as i
    inner join main.dim_store as d on i.store_id = d.store_id
    inner join main.dim_product as p on i.product_id = p.product_id
    where {where}
      and i.snapshot_date = (select max(snapshot_date) from main.mart_inventory as i where {where})
      and (i.days_of_cover < 3 or i.on_hand_qty = 0)
    order by i.days_of_cover nulls first, i.avg_daily_units_trailing desc
    """,
    params + params,
)

c = st.columns(4)
c[0].metric("Stockout rate", pct(kpi.stockout_rate))
c[1].metric("Stockout days", number(kpi.stockout_days), help="Store x product days")
c[2].metric("Store-SKUs affected", number(kpi.skus_affected))
c[3].metric("Low cover now (<3 days)", number(len(latest)), help="On the last date in the range")

trend = query(
    f"""
    select date_trunc('week', i.snapshot_date) as week, i.category,
           avg(case when i.is_stockout then 1.0 else 0 end) as stockout_rate
    from main.mart_inventory as i where {where}
    group by 1, 2 order by 1, 2
    """,
    params,
)
if not empty_notice(trend):
    fig = px.line(trend, x="week", y="stockout_rate", color="category",
                  title="Weekly stockout rate by category", labels={"stockout_rate": "", "week": ""})
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, width="stretch")

    worst = query(
        f"""
        select d.store_name, p.product_name, p.category,
               sum(case when i.is_stockout then 1 else 0 end) as stockout_days,
               avg(case when i.is_stockout then 1.0 else 0 end) as stockout_rate,
               avg(i.days_of_cover) as avg_days_of_cover,
               sum(i.units_sold) as units_sold
        from main.mart_inventory as i
        inner join main.dim_store as d on i.store_id = d.store_id
        inner join main.dim_product as p on i.product_id = p.product_id
        where {where}
        group by all
        having sum(case when i.is_stockout then 1 else 0 end) > 0
        order by stockout_days desc
        limit 25
        """,
        params,
    )
    left, right = st.columns(2)
    left.subheader("Most stocked-out store x product")
    left.dataframe(
        worst, hide_index=True, width="stretch",
        column_config={
            "stockout_rate": st.column_config.NumberColumn("Stockout rate", format="percent"),
            "avg_days_of_cover": st.column_config.NumberColumn("Avg days of cover", format="%.1f"),
        },
    )
    right.subheader("Out of stock or under 3 days of cover")
    right.dataframe(
        latest, hide_index=True, width="stretch",
        column_config={
            "avg_daily_units_trailing": st.column_config.NumberColumn("Avg daily units", format="%.2f"),
            "days_of_cover": st.column_config.NumberColumn("Days of cover", format="%.1f"),
        },
    )
