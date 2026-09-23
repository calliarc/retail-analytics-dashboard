with bounds as (
    select min(order_date) as min_date, max(order_date) as max_date
    from {{ ref('stg_orders') }}
),

days as (
    select cast(unnest(generate_series(min_date, max_date, interval 1 day)) as date) as date_day
    from bounds
)

select
    date_day,
    cast(date_trunc('week', date_day) as date)  as week_start,
    cast(date_trunc('month', date_day) as date) as month_start,
    extract(year from date_day)                 as year,
    extract(quarter from date_day)              as quarter,
    extract(month from date_day)                as month,
    strftime(date_day, '%b')                    as month_name,
    extract(isodow from date_day)               as iso_day_of_week,
    strftime(date_day, '%a')                    as day_name,
    extract(isodow from date_day) in (6, 7)     as is_weekend
from days
