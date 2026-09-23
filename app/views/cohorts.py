"""Monthly acquisition cohorts: retention and repeat-purchase rate."""

import plotly.express as px
import streamlit as st

from common import SYNTHETIC_NOTE, empty_notice, get_filters, pct, query

f = get_filters()
st.title("Customer cohorts")
st.caption(
    "Loyalty members grouped by the month of their first order. Only the date filter applies "
    "here (it selects cohort months); store and category filters do not. " + SYNTHETIC_NOTE
)

metric = st.radio(
    "Metric",
    ["retention_rate", "cumulative_repeat_rate"],
    horizontal=True,
    format_func=lambda m: {"retention_rate": "Retention (active in month N)",
                           "cumulative_repeat_rate": "Cumulative repeat rate"}[m],
)
max_months = st.slider("Months since first order", 3, 24, 12)

df = query(
    f"""
    select strftime(cohort_month, '%Y-%m') as cohort, cohort_size, months_since_first, {metric} as value
    from main.mart_cohorts
    where cohort_month between date_trunc('month', ?::date) and ? and months_since_first <= ?
    order by cohort_month, months_since_first
    """,
    [f.start, f.end, max_months],
)

if not empty_notice(df):
    grid = df.pivot(index="cohort", columns="months_since_first", values="value")
    fig = px.imshow(grid, color_continuous_scale="Blues", aspect="auto", text_auto=".0%",
                    labels={"x": "Months since first order", "y": "Cohort", "color": ""})
    fig.update_layout(height=max(400, 24 * len(grid)))
    fig.update_coloraxes(colorbar_tickformat=".0%")
    st.plotly_chart(fig, width="stretch")

    left, right = st.columns(2)
    sizes = df.drop_duplicates("cohort")[["cohort", "cohort_size"]]
    left.plotly_chart(
        px.bar(sizes, x="cohort", y="cohort_size", title="New members per cohort",
               labels={"cohort": "", "cohort_size": "customers"}),
        width="stretch",
    )
    curve = df[df["months_since_first"] > 0].groupby("months_since_first", as_index=False)["value"].mean()
    fig = px.line(curve, x="months_since_first", y="value", markers=True,
                  title="Average across cohorts",
                  labels={"months_since_first": "Months since first order", "value": ""})
    fig.update_yaxes(tickformat=".0%")
    right.plotly_chart(fig, width="stretch")

    m3 = df[df["months_since_first"] == 3]["value"].mean()
    st.markdown(f"Average {metric.replace('_', ' ')} at month 3: **{pct(m3)}**.")
