-- mart_daily_sales and mart_margin must add up to the fact table.
with f as (select sum(net_revenue) as v, sum(gross_margin) as m from {{ ref('fct_sales') }}),
     d as (select sum(net_revenue) as v, sum(gross_margin) as m from {{ ref('mart_daily_sales') }}),
     g as (select sum(net_revenue) as v, sum(gross_margin) as m from {{ ref('mart_margin') }})
select *
from f, d, g
where abs(f.v - d.v) > 0.01 or abs(f.v - g.v) > 0.01
   or abs(f.m - d.m) > 0.01 or abs(f.m - g.m) > 0.01
