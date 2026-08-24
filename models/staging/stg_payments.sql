select
    cast(payment_id as varchar) as payment_id,
    cast(booking_id as varchar) as booking_id,
    cast(restaurant_id as varchar) as restaurant_id,
    cast(paid_at as timestamp) as paid_at,
    upper(trim(currency)) as currency,
    cast(gross_amount as double) as gross_amount,
    cast(platform_fee as double) as platform_fee,
    upper(trim(payment_status)) as payment_status
from read_parquet('{{ var("raw_data_path") }}/payments.parquet')