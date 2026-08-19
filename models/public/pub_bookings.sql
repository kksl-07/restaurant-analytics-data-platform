{{ config(
    post_hook="
      COPY (SELECT * FROM {{ this }})
      TO '/app/exports/cleaned/bookings_clean.csv'
      (FORMAT csv, HEADER, DELIMITER ',')
    "
) }}

select
    booking_id,
    booking_created_at,
    meal_at,
    restaurant_id,
    user_id,
    party_size,
    booking_status,
    channel
from {{ ref('stg_bookings') }}
where booking_id is not null
  and restaurant_id is not null
  and user_id is not null
  and party_size > 0
  and booking_status in ('CANCELLED', 'CONFIRMED', 'CREATED', 'FULFILLED', 'NO_SHOW')