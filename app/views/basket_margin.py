"""Market basket (product pairs) and margin analysis."""

import plotly.express as px
import streamlit as st

from common import SYNTHETIC_NOTE, empty_notice, get_filters, query

f = get_filters()
st.title("Basket & margin")
st.caption(SYNTHETIC_NOTE)

st.subheader("Products bought together")
st.caption(
    "Computed over all orders (not affected by date or store filters). The category filter keeps "
    "pairs where either product is in a selected category. Lift > 1 means the pair is bought "
    "together more often than chance."
)
c1, c2 = st.columns(2)
min_orders = c1.slider("Minimum orders together", 3, 500, 20)
sort_by = c2.radio("Sort by", ["lift", "pair_orders", "attach_rate_a_to_b"], horizontal=True,
                   format_func=lambda m: m.replace("_", " "))
cats = list(f.categories)
pairs = query(
    f"""
    select product_a_name, product_a_category, product_b_name, product_b_category,
           pair_orders, support, attach_rate_a_to_b, attach_rate_b_to_a, lift
    from main.mart_basket
    where pair_orders >= ?
      and (list_contains(?, product_a_category) or list_contains(?, product_b_category))
    order by {sort_by} desc
    limit 50
    """,
    [min_orders, cats, cats],
)
if not empty_notice(pairs):
    st.dataframe(
        pairs, hide_index=True, width="stretch",
        column_config={
            "support": st.column_config.NumberColumn("Support", format="percent"),
            "attach_rate_a_to_b": st.column_config.NumberColumn("Attach A->B", format="percent"),
            "attach_rate_b_to_a": st.column_config.NumberColumn("Attach B->A", format="percent"),
            "lift": st.column_config.NumberColumn("Lift", format="%.2f"),
        },
    )

st.subheader("Margin by category")
st.caption("From mart_margin (monthly grain): months overlapping the selected date range are included.")
where, params = f.clause(date_col=None, store_col="m.store_id", category_col="m.category")
margin = query(
    f"""
    select m.category,
           sum(m.net_revenue) as net_revenue,
           sum(m.gross_margin) as gross_margin,
           sum(m.gross_margin) / nullif(sum(m.net_revenue), 0) as gross_margin_pct,
           sum(m.discount_amount) / nullif(sum(m.gross_revenue), 0) as discount_rate
    from main.mart_margin as m
    where {where} and m.month_start between date_trunc('month', ?::date) and ?
    group by 1 order by net_revenue desc
    """,
    params + [f.start, f.end],
)
if not empty_notice(margin):
    left, right = st.columns(2)
    fig = px.bar(margin, x="category", y="gross_margin_pct", title="Gross margin % (after discounts)",
                 labels={"category": "", "gross_margin_pct": ""})
    fig.update_yaxes(tickformat=".0%")
    left.plotly_chart(fig, width="stretch")
    fig = px.scatter(margin, x="discount_rate", y="gross_margin_pct", size="net_revenue", color="category",
                     title="Discount rate vs margin", labels={"discount_rate": "Discount rate",
                                                              "gross_margin_pct": "Gross margin %"})
    fig.update_xaxes(tickformat=".0%")
    fig.update_yaxes(tickformat=".0%")
    right.plotly_chart(fig, width="stretch")
