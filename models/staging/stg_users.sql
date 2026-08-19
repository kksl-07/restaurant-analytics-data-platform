select
    cast(user_id as varchar) as user_id,
    cast(created_at as timestamp) as user_created_at,
    upper(trim(country)) as user_country,
    cast(marketing_opt_in as boolean) as marketing_opt_in
from read_parquet('/app/data/raw/users.parquet')