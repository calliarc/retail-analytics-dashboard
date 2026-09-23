select *
from {{ ref('mart_inventory') }}
where on_hand_qty < 0 or on_order_qty < 0 or units_received < 0 or units_sold < 0
   or (is_stockout and on_hand_qty <> 0)
