select
    cast(store_id as integer)       as store_id,
    cast(store_code as varchar)     as store_code,
    cast(store_name as varchar)     as store_name,
    cast(city as varchar)           as city,
    cast(region as varchar)         as region,
    cast(store_format as varchar)   as store_format,
    cast(square_feet as integer)    as square_feet,
    cast(open_date as date)         as open_date
from {{ source('raw', 'stores') }}
