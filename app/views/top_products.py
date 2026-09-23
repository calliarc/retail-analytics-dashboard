"""Top products by revenue, units or gross margin."""

import plotly.express as px
import streamlit as st

from common import SYNTHETIC_NOTE, empty_notice, get_filters, query

f = get_filters()
st.title("Top products")
st.caption(SYNTHETIC_NOTE)

c1, c2 = st.columns([2, 1])
metric = c1.radio("Rank by", ["net_revenue", "units", "gross_margin"], horizontal=True,
                  format_func=lambda m: m.replace("_", " "))
top_n = c2.slider("Show top", 5, 50, 15, step=5)

where, params = f.clause(date_col="s.order_date", store_col="s.store_id", category_col="s.category")
df = query(
    f"""
    select p.product_name, p.sku, p.category, p.brand,
           sum(s.quantity)          as units,
           sum(s.net_revenue)       as net_revenue,
           sum(s.gross_margin)      as gross_margin,
           sum(s.gross_margin) / nullif(sum(s.net_revenue), 0) as gross_margin_pct,
           count(distinct s.order_id) as orders,
           sum(case when s.is_promo then s.quantity else 0 end) / sum(s.quantity) as promo_unit_share
    from main.fct_sales as s
    inner join main.dim_product as p on s.product_id = p.product_id
    where {where}
    group by all
    order by {metric} desc
    limit {int(top_n)}
    """,
    params,
)

if not empty_notice(df):
    fig = px.bar(df, x=metric, y="product_name", color="category", orientation="h",
                 labels={metric: metric.replace("_", " "), "product_name": ""},
                 height=max(350, 28 * len(df)))
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(
        df,
        hide_index=True,
        width="stretch",
        column_config={
            "net_revenue": st.column_config.NumberColumn("Net revenue", format="$%.0f"),
            "gross_margin": st.column_config.NumberColumn("Gross margin", format="$%.0f"),
            "gross_margin_pct": st.column_config.NumberColumn("Margin %", format="percent"),
            "promo_unit_share": st.column_config.NumberColumn("Promo units", format="percent"),
        },
    )
