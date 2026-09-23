select
    product_id,
    sku,
    product_name,
    category,
    brand,
    unit_cost,
    unit_price,
    unit_price - unit_cost                                          as unit_margin,
    cast(round((unit_price - unit_cost) / nullif(unit_price, 0), 4) as double) as list_margin_pct,
    case
        when unit_price < 5 then 'under 5'
        when unit_price < 20 then '5-20'
        when unit_price < 50 then '20-50'
        else '50+'
    end                                                             as price_band
from {{ ref('stg_products') }}
