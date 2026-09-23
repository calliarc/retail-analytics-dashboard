select
    cast(order_line_id as bigint)           as order_line_id,
    cast(order_id as bigint)                as order_id,
    cast(line_number as integer)            as line_number,
    cast(product_id as integer)             as product_id,
    cast(quantity as integer)               as quantity,
    cast(unit_price as decimal(12, 2))      as unit_price,
    cast(discount_pct as decimal(5, 2))     as discount_pct,
    cast(promo_id as integer)               as promo_id
from {{ source('raw', 'order_lines') }}
