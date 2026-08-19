-- Booking rates are proportions and must always
-- remain within the inclusive [0, 1] interval.

select
    restaurant_id,
    booking_cancellation_rate,
    no_show_rate
from {{ ref('mart_restaurant_kpis') }}
where booking_cancellation_rate < 0
   or booking_cancellation_rate > 1
   or no_show_rate < 0
   or no_show_rate > 1