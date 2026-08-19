-- Payments exposed by the public layer must never contain
-- negative gross amounts or platform fees.

select
    payment_id,
    booking_id,
    restaurant_id,
    gross_amount,
    platform_fee
from {{ ref('pub_payments') }}
where gross_amount < 0
   or platform_fee < 0