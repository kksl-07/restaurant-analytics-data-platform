from __future__ import annotations

import os
from pathlib import Path

import pandas as pd


# =========================
# PATHS
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_MART_PATH = PROJECT_ROOT / "exports" / "marts" / "restaurant_kpis.csv"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "exports" / "reports" / "summary_report.md"

mart_path = Path(
    os.getenv("MART_PATH", DEFAULT_MART_PATH)
)

report_path = Path(
    os.getenv("REPORT_PATH", DEFAULT_REPORT_PATH)
)

report_path.parent.mkdir(parents=True, exist_ok=True)


# =========================
# REPORT GENERATION
# =========================

if mart_path.exists():
    df = pd.read_csv(mart_path)

    total_restaurants = len(df)

    total_bookings = (
        int(df["total_bookings"].sum())
        if "total_bookings" in df.columns
        else 0
    )

    total_booked_covers = (
        int(df["booked_covers"].sum())
        if "booked_covers" in df.columns
        else 0
    )

    total_fulfilled_covers = (
        int(df["fulfilled_covers"].sum())
        if "fulfilled_covers" in df.columns
        else 0
    )

    total_paid_bookings = (
        int(df["paid_bookings"].sum())
        if "paid_bookings" in df.columns
        else 0
    )

    total_revenue_eur = (
        float(df["total_gross_revenue_in_eur"].sum())
        if "total_gross_revenue_in_eur" in df.columns
        else 0.0
    )

    total_revenue_gbp = (
        float(df["total_gross_revenue_in_gbp"].sum())
        if "total_gross_revenue_in_gbp" in df.columns
        else 0.0
    )

    total_platform_fee_eur = (
        float(df["total_platform_fee_in_eur"].sum())
        if "total_platform_fee_in_eur" in df.columns
        else 0.0
    )

    total_platform_fee_gbp = (
        float(df["total_platform_fee_in_gbp"].sum())
        if "total_platform_fee_in_gbp" in df.columns
        else 0.0
    )

    total_merchant_proceeds_eur = (
        float(df["merchant_proceeds_in_eur"].sum())
        if "merchant_proceeds_in_eur" in df.columns
        else 0.0
    )

    total_merchant_proceeds_gbp = (
        float(df["merchant_proceeds_in_gbp"].sum())
        if "merchant_proceeds_in_gbp" in df.columns
        else 0.0
    )

    avg_paid_booking_value_eur = (
        total_revenue_eur / total_paid_bookings
        if total_paid_bookings > 0
        else 0.0
    )

    avg_paid_booking_value_gbp = (
        total_revenue_gbp / total_paid_bookings
        if total_paid_bookings > 0
        else 0.0
    )

    avg_cancellation_rate = (
        float(df["booking_cancellation_rate"].mean())
        if "booking_cancellation_rate" in df.columns and not df.empty
        else 0.0
    )

    avg_no_show_rate = (
        float(df["no_show_rate"].mean())
        if "no_show_rate" in df.columns and not df.empty
        else 0.0
    )

    top_restaurant_by_bookings = "N/A"

    if (
        not df.empty
        and {"restaurant_name", "total_bookings"}.issubset(df.columns)
    ):
        top_restaurant_by_bookings = (
            df.sort_values(
                "total_bookings",
                ascending=False,
            )
            .iloc[0]["restaurant_name"]
        )

    top_restaurant_by_revenue_eur = "N/A"

    if (
        not df.empty
        and {
            "restaurant_name",
            "total_gross_revenue_in_eur",
        }.issubset(df.columns)
    ):
        top_restaurant_by_revenue_eur = (
            df.sort_values(
                "total_gross_revenue_in_eur",
                ascending=False,
            )
            .iloc[0]["restaurant_name"]
        )

    content = f"""# Summary Report

## Pipeline status

Pipeline completed successfully.

## Produced artifacts

- Cleaned tables in `exports/cleaned/`
- Final mart in `exports/marts/restaurant_kpis.csv`

## Operational KPI summary

- Total restaurants: {total_restaurants}
- Total bookings: {total_bookings}
- Total booked covers: {total_booked_covers}
- Total fulfilled covers: {total_fulfilled_covers}
- Total paid bookings: {total_paid_bookings}
- Average booking cancellation rate: {avg_cancellation_rate:.4f}
- Average no-show rate: {avg_no_show_rate:.4f}
- Top restaurant by bookings: {top_restaurant_by_bookings}

## Revenue KPI summary

- Total gross revenue (EUR): {total_revenue_eur:.2f}
- Total gross revenue (GBP): {total_revenue_gbp:.2f}
- Total platform fee (EUR): {total_platform_fee_eur:.2f}
- Total platform fee (GBP): {total_platform_fee_gbp:.2f}
- Total merchant proceeds (EUR): {total_merchant_proceeds_eur:.2f}
- Total merchant proceeds (GBP): {total_merchant_proceeds_gbp:.2f}
- Average paid booking value (EUR): {avg_paid_booking_value_eur:.2f}
- Average paid booking value (GBP): {avg_paid_booking_value_gbp:.2f}
- Top restaurant by revenue (EUR): {top_restaurant_by_revenue_eur}

## Assumptions

- Revenue KPIs only include payments with status `PAID`
- Currency conversion uses fixed project FX rates for deterministic offline execution
- The synthetic payment model assumes one payment record per booking
"""

else:
    content = f"""# Summary Report

## Pipeline status

The KPI mart output file was not found.

Expected mart:

`{mart_path}`

Please check:

- dbt model execution
- output export paths
- logs in `logs/`
"""


# =========================
# WRITE REPORT
# =========================

report_path.write_text(
    content,
    encoding="utf-8",
)

print(f"Report written to: {report_path}")