{#- Grain: one row per order line. Revenue is net of promotional discount. -#}
with lines as (
    select * from {{ ref('stg_order_lines') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

products as (
    select product_id, category, unit_cost from {{ ref('stg_products') }}
),

joined as (
    select
        l.order_line_id,
        l.order_id,
        l.line_number,
        o.order_date,
        o.order_ts,
        o.store_id,
        o.customer_id,
        o.customer_id is not null                               as is_member,
        o.channel,
        l.product_id,
        p.category,
        l.promo_id,
        l.promo_id is not null                                  as is_promo,
        l.quantity,
        l.unit_price,
        l.discount_pct,
        p.unit_cost,
        cast(l.quantity * l.unit_price as decimal(18, 2))       as gross_revenue,
        cast(round(l.quantity * l.unit_price * l.discount_pct, 2) as decimal(18, 2)) as discount_amount
    from lines as l
    inner join orders as o on l.order_id = o.order_id
    inner join products as p on l.product_id = p.product_id
)

select
    *,
    gross_revenue - discount_amount                             as net_revenue,
    cast(quantity * unit_cost as decimal(18, 2))                as cogs,
    gross_revenue - discount_amount
        - cast(quantity * unit_cost as decimal(18, 2))          as gross_margin
from joined
