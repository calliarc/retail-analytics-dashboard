{#- Monthly acquisition cohorts for loyalty members (guests excluded).
    Grain: cohort_month x months_since_first (0 = acquisition month).
    retention_rate           = active customers in that month / cohort size
    cumulative_repeat_rate   = customers who placed a 2nd order by that month / cohort size -#}
with member_orders as (
    select customer_id, order_id, min(order_date) as order_date, sum(net_revenue) as net_revenue
    from {{ ref('fct_sales') }}
    where customer_id is not null
    group by customer_id, order_id
),

ranked as (
    select
        *,
        row_number() over (partition by customer_id order by order_date, order_id) as order_seq
    from member_orders
),

customers as (
    select
        customer_id,
        cast(date_trunc('month', min(order_date)) as date)                          as cohort_month,
        cast(date_trunc('month', min(case when order_seq = 2 then order_date end)) as date)
                                                                                    as second_order_month
    from ranked
    group by customer_id
),

cohort_sizes as (
    select cohort_month, count(*) as cohort_size
    from customers
    group by cohort_month
),

months as (
    select distinct cast(date_trunc('month', order_date) as date) as activity_month
    from member_orders
),

grid as (
    select
        c.cohort_month,
        m.activity_month,
        datediff('month', c.cohort_month, m.activity_month) as months_since_first
    from cohort_sizes as c
    inner join months as m on m.activity_month >= c.cohort_month
),

activity as (
    select
        c.cohort_month,
        cast(date_trunc('month', r.order_date) as date) as activity_month,
        count(distinct r.customer_id)                   as active_customers,
        count(*)                                        as orders,
        sum(r.net_revenue)                              as net_revenue
    from ranked as r
    inner join customers as c on r.customer_id = c.customer_id
    group by 1, 2
),

repeaters as (
    select
        g.cohort_month,
        g.months_since_first,
        count(c.customer_id) as repeat_customers_cumulative
    from grid as g
    left join customers as c
        on c.cohort_month = g.cohort_month
        and c.second_order_month <= g.activity_month
    group by 1, 2
)

select
    concat_ws('|', strftime(g.cohort_month, '%Y-%m'), g.months_since_first)    as cohort_key,
    g.cohort_month,
    g.activity_month,
    g.months_since_first,
    s.cohort_size,
    coalesce(a.active_customers, 0)                                     as active_customers,
    coalesce(a.orders, 0)                                               as orders,
    coalesce(a.net_revenue, 0)                                          as net_revenue,
    cast(coalesce(a.active_customers, 0) as double) / s.cohort_size     as retention_rate,
    r.repeat_customers_cumulative,
    cast(r.repeat_customers_cumulative as double) / s.cohort_size       as cumulative_repeat_rate
from grid as g
inner join cohort_sizes as s on g.cohort_month = s.cohort_month
inner join repeaters as r
    on g.cohort_month = r.cohort_month
    and g.months_since_first = r.months_since_first
left join activity as a
    on g.cohort_month = a.cohort_month
    and g.activity_month = a.activity_month
