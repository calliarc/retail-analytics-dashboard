select
    cast(customer_id as bigint)     as customer_id,
    cast(signup_date as date)       as signup_date,
    cast(home_store_id as integer)  as home_store_id,
    cast(loyalty_tier as varchar)   as loyalty_tier,
    cast(age_band as varchar)       as age_band
from {{ source('raw', 'customers') }}
