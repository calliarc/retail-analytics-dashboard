-- net = gross - discount, margin = net - cogs, and no negative quantities or revenue.
select *
from {{ ref('fct_sales') }}
where abs(net_revenue - (gross_revenue - discount_amount)) > 0.01
   or abs(gross_margin - (net_revenue - cogs)) > 0.01
   or quantity <= 0
   or net_revenue < 0
