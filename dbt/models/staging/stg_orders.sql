select
    cast(order_id as bigint)        as order_id,
    cast(order_ts as timestamp)     as order_ts,
    cast(order_date as date)        as order_date,
    cast(store_id as integer)       as store_id,
    cast(customer_id as bigint)     as customer_id,
    cast(channel as varchar)        as channel
from {{ source('raw', 'orders') }}
