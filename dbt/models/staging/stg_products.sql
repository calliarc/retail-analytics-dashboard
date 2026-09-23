select
    cast(product_id as integer)             as product_id,
    cast(sku as varchar)                    as sku,
    cast(product_name as varchar)           as product_name,
    cast(category as varchar)               as category,
    cast(brand as varchar)                  as brand,
    cast(unit_cost as decimal(12, 2))       as unit_cost,
    cast(unit_price as decimal(12, 2))      as unit_price
from {{ source('raw', 'products') }}
