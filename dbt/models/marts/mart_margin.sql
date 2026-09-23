{#- Grain: month x store x product. -#}
with monthly as (
    select
        cast(date_trunc('month', order_date) as date)           as month_start,
        store_id,
        product_id,
        sum(quantity)                                           as units,
        sum(gross_revenue)                                      as gross_revenue,
        sum(discount_amount)                                    as discount_amount,
        sum(net_revenue)                                        as net_revenue,
        sum(cogs)                                               as cogs,
        sum(gross_margin)                                       as gross_margin,
        sum(case when is_promo then net_revenue else 0 end)     as promo_net_revenue
    from {{ ref('fct_sales') }}
    group by 1, 2, 3
)

select
    concat_ws('|', strftime(m.month_start, '%Y-%m'), m.store_id, m.product_id) as margin_key,
    m.month_start,
    m.store_id,
    m.product_id,
    p.category,
    m.units,
    m.gross_revenue,
    m.discount_amount,
    m.net_revenue,
    m.cogs,
    m.gross_margin,
    cast(m.gross_margin / nullif(m.net_revenue, 0) as double)       as gross_margin_pct,
    cast(m.discount_amount / nullif(m.gross_revenue, 0) as double)  as discount_rate,
    cast(m.promo_net_revenue / nullif(m.net_revenue, 0) as double)  as promo_revenue_share
from monthly as m
inner join {{ ref('dim_product') }} as p on m.product_id = p.product_id
