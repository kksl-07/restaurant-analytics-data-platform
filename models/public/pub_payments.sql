{{ config(
    post_hook="
      COPY (SELECT * FROM {{ this }})
      TO '/app/exports/cleaned/payments_clean.csv'
      (FORMAT csv, HEADER, DELIMITER ',')
    "
) }}

select
    payment_id,
    booking_id,
    restaurant_id,
    paid_at,
    currency,
    gross_amount,
    platform_fee,
    payment_status
from {{ ref('stg_payments') }}
where payment_id is not null
  and booking_id is not null
  and restaurant_id is not null
  and currency in ('EUR', 'GBP')
  and gross_amount is not null
  and gross_amount >= 0
  and platform_fee is not null
  and platform_fee >= 0
  and payment_status in ('PAID', 'FAILED', 'REFUNDED')