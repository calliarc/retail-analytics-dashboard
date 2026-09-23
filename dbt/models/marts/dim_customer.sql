with customers as (
    select * from {{ ref('stg_customers') }}
),

order_totals as (
    select
        customer_id,
        order_id,
        min(order_date)   as order_date,
        sum(net_revenue)  as order_net_revenue
    from {{ ref('fct_sales') }}
    where customer_id is not null
    group by customer_id, order_id
),

stats as (
    select
        customer_id,
        min(order_date)          as first_order_date,
        max(order_date)          as last_order_date,
        count(*)                 as order_count,
        sum(order_net_revenue)   as lifetime_net_revenue
    from order_totals
    group by customer_id
)

select
    c.customer_id,
    c.signup_date,
    c.home_store_id,
    c.loyalty_tier,
    c.age_band,
    s.first_order_date,
    s.last_order_date,
    cast(date_trunc('month', s.first_order_date) as date)   as cohort_month,
    coalesce(s.order_count, 0)                              as order_count,
    coalesce(s.lifetime_net_revenue, 0)                     as lifetime_net_revenue,
    coalesce(s.order_count, 0) >= 2                         as is_repeat_customer
from customers as c
left join stats as s on c.customer_id = s.customer_id
