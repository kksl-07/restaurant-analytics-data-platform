{{ config(
    post_hook="
      COPY (SELECT * FROM {{ this }})
      TO '{{ var('cleaned_data_path') }}/restaurants_clean.csv'
      (FORMAT csv, HEADER, DELIMITER ',')
    "
) }}

select
    restaurant_id,
    restaurant_name,
    country,
    city,
    cuisine_type,
    price_range,
    opened_date,
    is_active
from {{ ref('stg_restaurants') }}
where restaurant_id is not null
  and restaurant_name is not null
  and is_active = true