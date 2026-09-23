-- Pairs are stored once (a < b) and rates are proper proportions.
select *
from {{ ref('mart_basket') }}
where product_a_id >= product_b_id
   or support not between 0 and 1
   or attach_rate_a_to_b not between 0 and 1
   or attach_rate_b_to_a not between 0 and 1
   or lift <= 0
