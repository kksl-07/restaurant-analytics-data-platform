select
    cast(restaurant_id as varchar) as restaurant_id,
    trim(name) as restaurant_name,
    upper(trim(country)) as country,
    trim(city) as city,
    trim(cuisine_type) as cuisine_type,
    trim(price_range) as price_range,
    cast(opened_date as date) as opened_date,
    cast(is_active as boolean) as is_active
from read_parquet('{{ var("raw_data_path") }}/restaurants.parquet')