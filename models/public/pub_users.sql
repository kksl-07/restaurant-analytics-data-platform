{{ config(
    post_hook="
      COPY (SELECT * FROM {{ this }})
      TO '{{ var('cleaned_data_path') }}/users_clean.csv'
      (FORMAT csv, HEADER, DELIMITER ',')
    "
) }}

select
    user_id,
    user_created_at,
    user_country,
    marketing_opt_in
from {{ ref('stg_users') }}
where user_id is not null