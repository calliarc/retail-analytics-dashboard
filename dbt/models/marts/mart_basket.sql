{#- Product-pair co-occurrence across all orders.
    One row per unordered pair (product_a_id < product_b_id).
    attach_rate_a_to_b = share of orders containing A that also contain B. -#}
with order_products as (
    select distinct order_id, product_id
    from {{ ref('fct_sales') }}
),

total as (
    select count(distinct order_id) as total_orders from order_products
),

product_orders as (
    select product_id, count(*) as orders_with_product
    from order_products
    group by product_id
),

pairs as (
    select
        a.product_id as product_a_id,
        b.product_id as product_b_id,
        count(*)     as pair_orders
    from order_products as a
    inner join order_products as b
        on a.order_id = b.order_id
        and a.product_id < b.product_id
    group by 1, 2
    having count(*) >= {{ var('basket_min_pair_orders', 3) }}
)

select
    concat_ws('|', p.product_a_id, p.product_b_id)                             as pair_key,
    p.product_a_id,
    da.product_name                                                     as product_a_name,
    da.category                                                         as product_a_category,
    p.product_b_id,
    db.product_name                                                     as product_b_name,
    db.category                                                         as product_b_category,
    p.pair_orders,
    pa.orders_with_product                                              as orders_with_a,
    pb.orders_with_product                                              as orders_with_b,
    t.total_orders,
    cast(p.pair_orders as double) / t.total_orders                      as support,
    cast(p.pair_orders as double) / pa.orders_with_product              as attach_rate_a_to_b,
    cast(p.pair_orders as double) / pb.orders_with_product              as attach_rate_b_to_a,
    (cast(p.pair_orders as double) / t.total_orders)
        / ((cast(pa.orders_with_product as double) / t.total_orders)
           * (cast(pb.orders_with_product as double) / t.total_orders)) as lift
from pairs as p
cross join total as t
inner join product_orders as pa on p.product_a_id = pa.product_id
inner join product_orders as pb on p.product_b_id = pb.product_id
inner join {{ ref('dim_product') }} as da on p.product_a_id = da.product_id
inner join {{ ref('dim_product') }} as db on p.product_b_id = db.product_id
