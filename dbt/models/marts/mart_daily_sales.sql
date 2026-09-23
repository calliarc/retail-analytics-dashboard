{#- Grain: date x store x category. `orders` counts orders containing the category,
    so it is not additive across categories; use fct_sales for total order counts. -#}
select
    concat_ws('|', order_date, store_id, category)        as daily_sales_key,
    order_date                                              as date_day,
    store_id,
    category,
    count(distinct order_id)                                as orders,
    count(distinct customer_id)                             as member_customers,
    sum(quantity)                                           as units,
    sum(gross_revenue)                                      as gross_revenue,
    sum(discount_amount)                                    as discount_amount,
    sum(net_revenue)                                        as net_revenue,
    sum(cogs)                                               as cogs,
    sum(gross_margin)                                       as gross_margin,
    sum(case when is_promo then net_revenue else 0 end)     as promo_net_revenue
from {{ ref('fct_sales') }}
group by order_date, store_id, category
