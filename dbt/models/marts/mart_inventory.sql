{#- Grain: date x store x product (only days the store was open).
    A stockout day is a day that closed with zero units on hand.
    days_of_cover = on-hand units / trailing average daily units sold. -#}
{%- set window = var('inventory_trailing_days', 28) - 1 -%}
with snapshots as (
    select * from {{ ref('stg_inventory_snapshots') }}
),

daily_sales as (
    select order_date, store_id, product_id, sum(quantity) as units_sold
    from {{ ref('fct_sales') }}
    group by 1, 2, 3
),

joined as (
    select
        s.snapshot_date,
        s.store_id,
        s.product_id,
        s.on_hand_qty,
        s.on_order_qty,
        s.units_received,
        coalesce(d.units_sold, 0)   as units_sold,
        s.on_hand_qty = 0           as is_stockout
    from snapshots as s
    left join daily_sales as d
        on s.snapshot_date = d.order_date
        and s.store_id = d.store_id
        and s.product_id = d.product_id
),

windowed as (
    select
        *,
        avg(units_sold) over w                                  as avg_daily_units_trailing,
        sum(case when is_stockout then 1 else 0 end) over w     as stockout_days_trailing
    from joined
    window w as (
        partition by store_id, product_id
        order by snapshot_date
        rows between {{ window }} preceding and current row
    )
)

select
    concat_ws('|', w.snapshot_date, w.store_id, w.product_id)   as inventory_key,
    w.snapshot_date,
    w.store_id,
    w.product_id,
    p.category,
    w.on_hand_qty,
    w.on_order_qty,
    w.units_received,
    w.units_sold,
    w.is_stockout,
    cast(w.avg_daily_units_trailing as double)                    as avg_daily_units_trailing,
    w.stockout_days_trailing,
    cast(case
        when w.avg_daily_units_trailing > 0
            then w.on_hand_qty / w.avg_daily_units_trailing
    end as double)                                                as days_of_cover
from windowed as w
inner join {{ ref('dim_product') }} as p on w.product_id = p.product_id
