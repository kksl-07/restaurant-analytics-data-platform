with fx_rates as (
    select
        1.17 as gbp_to_eur,
        0.8547 as eur_to_gbp
),

restaurants as (
    select
        restaurant_id,
        restaurant_name,
        country,
        city,
        cuisine_type,
        price_range
    from {{ ref('pub_restaurants') }}
),

bookings as (
    select
        booking_id,
        restaurant_id,
        user_id,
        party_size,
        booking_status
    from {{ ref('pub_bookings') }}
),

payments as (
    select
        payment_id,
        booking_id,
        restaurant_id,
        currency,
        gross_amount,
        platform_fee,
        payment_status
    from {{ ref('pub_payments') }}
),

joined as (
    select
        r.restaurant_id,
        r.restaurant_name,
        r.country,
        r.city,
        r.cuisine_type,
        r.price_range,

        b.booking_id,
        b.user_id,
        b.party_size,
        b.booking_status,

        p.payment_id,
        p.currency,
        p.gross_amount,
        p.platform_fee,
        p.payment_status

    from restaurants r

    left join bookings b
        on r.restaurant_id = b.restaurant_id

    left join payments p
        on b.booking_id = p.booking_id
       and b.restaurant_id = p.restaurant_id
),

converted as (
    select
        j.*,

        case
            when j.currency = 'EUR' then j.gross_amount
            when j.currency = 'GBP' then j.gross_amount * fx.gbp_to_eur
            else null
        end as gross_amount_in_eur,

        case
            when j.currency = 'GBP' then j.gross_amount
            when j.currency = 'EUR' then j.gross_amount * fx.eur_to_gbp
            else null
        end as gross_amount_in_gbp,

        case
            when j.currency = 'EUR' then j.platform_fee
            when j.currency = 'GBP' then j.platform_fee * fx.gbp_to_eur
            else null
        end as platform_fee_in_eur,

        case
            when j.currency = 'GBP' then j.platform_fee
            when j.currency = 'EUR' then j.platform_fee * fx.eur_to_gbp
            else null
        end as platform_fee_in_gbp

    from joined j
    cross join fx_rates fx
),

final as (
    select
        restaurant_id,
        restaurant_name,
        country,
        city,
        cuisine_type,
        price_range,

        count(distinct booking_id) as total_bookings,

        count(
            distinct case
                when booking_status in ('CONFIRMED', 'FULFILLED')
                then booking_id
            end
        ) as confirmed_or_fulfilled_bookings,

        round(
            1.0 * count(
                distinct case
                    when booking_status = 'CANCELLED'
                    then booking_id
                end
            )
            / nullif(count(distinct booking_id), 0),
            4
        ) as booking_cancellation_rate,

        round(
            1.0 * count(
                distinct case
                    when booking_status = 'NO_SHOW'
                    then booking_id
                end
            )
            / nullif(count(distinct booking_id), 0),
            4
        ) as no_show_rate,

        coalesce(
            sum(party_size),
            0
        ) as booked_covers,

        coalesce(
            sum(
                case
                    when booking_status = 'FULFILLED'
                    then party_size
                    else 0
                end
            ),
            0
        ) as fulfilled_covers,

        count(distinct user_id) as unique_bookers,

        count(
            distinct case
                when payment_status = 'PAID'
                then booking_id
            end
        ) as paid_bookings,

        count(
            distinct case
                when payment_status = 'PAID'
                 and currency = 'EUR'
                then booking_id
            end
        ) as paid_bookings_eur,

        count(
            distinct case
                when payment_status = 'PAID'
                 and currency = 'GBP'
                then booking_id
            end
        ) as paid_bookings_gbp,

        round(
            coalesce(
                sum(
                    case
                        when payment_status = 'PAID'
                         and currency = 'EUR'
                        then gross_amount
                        else 0
                    end
                ),
                0
            ),
            2
        ) as gross_revenue_eur,

        round(
            coalesce(
                sum(
                    case
                        when payment_status = 'PAID'
                         and currency = 'GBP'
                        then gross_amount
                        else 0
                    end
                ),
                0
            ),
            2
        ) as gross_revenue_gbp,

        round(
            coalesce(
                sum(
                    case
                        when payment_status = 'PAID'
                         and currency = 'EUR'
                        then platform_fee
                        else 0
                    end
                ),
                0
            ),
            2
        ) as platform_fee_eur,

        round(
            coalesce(
                sum(
                    case
                        when payment_status = 'PAID'
                         and currency = 'GBP'
                        then platform_fee
                        else 0
                    end
                ),
                0
            ),
            2
        ) as platform_fee_gbp,

        round(
            coalesce(
                sum(
                    case
                        when payment_status = 'PAID'
                        then gross_amount_in_eur
                        else 0
                    end
                ),
                0
            ),
            2
        ) as total_gross_revenue_in_eur,

        round(
            coalesce(
                sum(
                    case
                        when payment_status = 'PAID'
                        then gross_amount_in_gbp
                        else 0
                    end
                ),
                0
            ),
            2
        ) as total_gross_revenue_in_gbp,

        round(
            coalesce(
                sum(
                    case
                        when payment_status = 'PAID'
                        then platform_fee_in_eur
                        else 0
                    end
                ),
                0
            ),
            2
        ) as total_platform_fee_in_eur,

        round(
            coalesce(
                sum(
                    case
                        when payment_status = 'PAID'
                        then platform_fee_in_gbp
                        else 0
                    end
                ),
                0
            ),
            2
        ) as total_platform_fee_in_gbp,

        round(
            coalesce(
                sum(
                    case
                        when payment_status = 'PAID'
                        then gross_amount_in_eur - platform_fee_in_eur
                        else 0
                    end
                ),
                0
            ),
            2
        ) as merchant_proceeds_in_eur,

        round(
            coalesce(
                sum(
                    case
                        when payment_status = 'PAID'
                        then gross_amount_in_gbp - platform_fee_in_gbp
                        else 0
                    end
                ),
                0
            ),
            2
        ) as merchant_proceeds_in_gbp,

        round(
            coalesce(
                avg(
                    case
                        when payment_status = 'PAID'
                        then gross_amount_in_eur
                        else null
                    end
                ),
                0
            ),
            2
        ) as avg_paid_booking_value_in_eur,

        round(
            coalesce(
                avg(
                    case
                        when payment_status = 'PAID'
                        then gross_amount_in_gbp
                        else null
                    end
                ),
                0
            ),
            2
        ) as avg_paid_booking_value_in_gbp

    from converted

    group by
        restaurant_id,
        restaurant_name,
        country,
        city,
        cuisine_type,
        price_range
)

select *
from final
order by
    total_gross_revenue_in_eur desc,
    total_bookings desc