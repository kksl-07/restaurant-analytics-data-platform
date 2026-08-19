-- Merchant proceeds represent the amount remaining after
-- deducting platform fees from gross paid transaction value.
--
-- Therefore:
--
-- gross revenue = platform fee + merchant proceeds
--
-- A small tolerance is allowed because monetary metrics
-- are rounded to two decimal places in the mart.

select
    restaurant_id,

    total_gross_revenue_in_eur,
    total_platform_fee_in_eur,
    merchant_proceeds_in_eur,

    total_gross_revenue_in_gbp,
    total_platform_fee_in_gbp,
    merchant_proceeds_in_gbp

from {{ ref('mart_restaurant_kpis') }}

where abs(
    total_gross_revenue_in_eur
    - (
        total_platform_fee_in_eur
        + merchant_proceeds_in_eur
    )
) > 0.02

or abs(
    total_gross_revenue_in_gbp
    - (
        total_platform_fee_in_gbp
        + merchant_proceeds_in_gbp
    )
) > 0.02