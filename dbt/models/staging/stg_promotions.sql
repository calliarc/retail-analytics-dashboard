select
    cast(promo_id as integer)               as promo_id,
    cast(promo_name as varchar)             as promo_name,
    cast(category as varchar)               as category,
    cast(start_date as date)                as start_date,
    cast(end_date as date)                  as end_date,
    cast(discount_pct as decimal(5, 2))     as discount_pct
from {{ source('raw', 'promotions') }}
