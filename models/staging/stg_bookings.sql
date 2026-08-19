select
    cast(booking_id as varchar) as booking_id,
    cast(created_at as timestamp) as booking_created_at,
    cast(meal_at as timestamp) as meal_at,
    cast(restaurant_id as varchar) as restaurant_id,
    cast(user_id as varchar) as user_id,
    cast(party_size as integer) as party_size,
    upper(trim(status)) as booking_status,
    lower(trim(channel)) as channel
from read_parquet('/app/data/raw/bookings.parquet')