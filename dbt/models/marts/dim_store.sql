select
    store_id,
    store_code,
    store_name,
    city,
    region,
    store_format,
    square_feet,
    open_date
from {{ ref('stg_stores') }}
