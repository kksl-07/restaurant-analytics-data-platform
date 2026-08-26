from __future__ import annotations

import os
from pathlib import Path

import duckdb

# =========================
# PATHS
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DUCKDB_PATH = PROJECT_ROOT / ".duckdb" / "local.duckdb"

DEFAULT_MART_PATH = PROJECT_ROOT / "exports" / "marts" / "restaurant_kpis.csv"

DEFAULT_REPORT_PATH = PROJECT_ROOT / "exports" / "reports" / "summary_report.md"

duckdb_path = Path(
    os.getenv(
        "DUCKDB_PATH",
        DEFAULT_DUCKDB_PATH,
    )
)

mart_path = Path(
    os.getenv(
        "MART_PATH",
        DEFAULT_MART_PATH,
    )
)

report_path = Path(
    os.getenv(
        "REPORT_PATH",
        DEFAULT_REPORT_PATH,
    )
)

mart_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)

report_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================
# CONSUMER DATA CONTRACT
# =========================

# Minimum schema required by this reporting consumer.
#
# The mart may expose additional columns without breaking
# the reporting layer.

REPORT_REQUIRED_COLUMNS = {
    "restaurant_name",
    "total_bookings",
    "booked_covers",
    "fulfilled_covers",
    "unique_bookers",
    "paid_bookings",
    "paid_bookings_eur",
    "paid_bookings_gbp",
    "booking_cancellation_rate",
    "no_show_rate",
    "gross_revenue_eur",
    "gross_revenue_gbp",
    "platform_fee_eur",
    "platform_fee_gbp",
    "total_gross_revenue_in_eur",
    "total_gross_revenue_in_gbp",
    "total_platform_fee_in_eur",
    "total_platform_fee_in_gbp",
    "merchant_proceeds_in_eur",
    "merchant_proceeds_in_gbp",
    "avg_paid_booking_value_in_eur",
    "avg_paid_booking_value_in_gbp",
}


# =========================
# VALIDATE DUCKDB
# =========================

if not duckdb_path.exists():
    raise FileNotFoundError(f"DuckDB database not found: {duckdb_path}")


# =========================
# READ VALIDATED MART
# =========================

print(f"Reading validated mart from DuckDB: {duckdb_path}")

with duckdb.connect(
    str(duckdb_path),
    read_only=True,
) as connection:
    try:
        df = connection.execute(
            """
            select *
            from main.mart_restaurant_kpis
            """
        ).df()

    except duckdb.Error as exc:
        raise RuntimeError(
            "Unable to read main.mart_restaurant_kpis "
            "from DuckDB. Ensure dbt build completed "
            "successfully."
        ) from exc


# =========================
# VALIDATE MART
# =========================

if df.empty:
    raise RuntimeError(
        "mart_restaurant_kpis is empty. Report generation has been stopped."
    )

missing_columns = REPORT_REQUIRED_COLUMNS - set(df.columns)

if missing_columns:
    raise RuntimeError(
        "mart_restaurant_kpis is missing columns "
        "required by the reporting layer: " + ", ".join(sorted(missing_columns))
    )


# =========================
# EXPORT VALIDATED MART
# =========================

# Export the complete mart.
#
# REPORT_REQUIRED_COLUMNS defines the minimum schema
# required by this consumer. It does not define or
# truncate the full mart schema.

df.to_csv(
    mart_path,
    index=False,
)

print(f"Validated mart exported to: {mart_path} ({len(df)} rows)")


# =========================
# REPORT AGGREGATIONS
# =========================

# The mart contains one row per restaurant.
#
# The reporting layer aggregates metrics already
# calculated by dbt. Business KPI definitions remain
# owned by the dbt transformation layer.

total_restaurants = len(df)

total_bookings = int(df["total_bookings"].sum())

total_booked_covers = int(df["booked_covers"].sum())

total_fulfilled_covers = int(df["fulfilled_covers"].sum())

total_unique_bookers = int(df["unique_bookers"].sum())

total_paid_bookings = int(df["paid_bookings"].sum())

total_paid_bookings_eur = int(df["paid_bookings_eur"].sum())

total_paid_bookings_gbp = int(df["paid_bookings_gbp"].sum())

gross_revenue_eur = float(df["gross_revenue_eur"].sum())

gross_revenue_gbp = float(df["gross_revenue_gbp"].sum())

platform_fee_eur = float(df["platform_fee_eur"].sum())

platform_fee_gbp = float(df["platform_fee_gbp"].sum())

total_gross_revenue_in_eur = float(df["total_gross_revenue_in_eur"].sum())

total_gross_revenue_in_gbp = float(df["total_gross_revenue_in_gbp"].sum())

total_platform_fee_in_eur = float(df["total_platform_fee_in_eur"].sum())

total_platform_fee_in_gbp = float(df["total_platform_fee_in_gbp"].sum())

merchant_proceeds_in_eur = float(df["merchant_proceeds_in_eur"].sum())

merchant_proceeds_in_gbp = float(df["merchant_proceeds_in_gbp"].sum())


# =========================
# REPORT-LEVEL STATISTICS
# =========================

# These are descriptive statistics over restaurant-level
# metrics already calculated by dbt.

avg_restaurant_cancellation_rate = float(df["booking_cancellation_rate"].mean())

avg_restaurant_no_show_rate = float(df["no_show_rate"].mean())


# =========================
# TOP RESTAURANTS
# =========================

top_restaurant_by_bookings = df.sort_values(
    "total_bookings",
    ascending=False,
).iloc[0]["restaurant_name"]

top_restaurant_by_revenue_eur = df.sort_values(
    "total_gross_revenue_in_eur",
    ascending=False,
).iloc[0]["restaurant_name"]


# =========================
# REPORT CONTENT
# =========================

content = f"""# Summary Report

## Pipeline status

Pipeline completed successfully.

All dbt transformations and data quality checks passed before
the reporting artifacts were generated.

## Produced artifacts

- Cleaned tables in `exports/cleaned/`
- Final mart in `exports/marts/restaurant_kpis.csv`
- Summary report in `exports/reports/summary_report.md`

## Operational KPI summary

- Total restaurants: {total_restaurants}
- Total bookings: {total_bookings}
- Total booked covers: {total_booked_covers}
- Total fulfilled covers: {total_fulfilled_covers}
- Total unique bookers: {total_unique_bookers}
- Total paid bookings: {total_paid_bookings}
- Paid bookings (EUR): {total_paid_bookings_eur}
- Paid bookings (GBP): {total_paid_bookings_gbp}
- Average restaurant cancellation rate: {avg_restaurant_cancellation_rate:.4f}
- Average restaurant no-show rate: {avg_restaurant_no_show_rate:.4f}
- Top restaurant by bookings: {top_restaurant_by_bookings}

## Revenue KPI summary

- Gross revenue (EUR): {gross_revenue_eur:.2f}
- Gross revenue (GBP): {gross_revenue_gbp:.2f}
- Platform fee (EUR): {platform_fee_eur:.2f}
- Platform fee (GBP): {platform_fee_gbp:.2f}
- Total gross revenue converted to EUR: {total_gross_revenue_in_eur:.2f}
- Total gross revenue converted to GBP: {total_gross_revenue_in_gbp:.2f}
- Total platform fee converted to EUR: {total_platform_fee_in_eur:.2f}
- Total platform fee converted to GBP: {total_platform_fee_in_gbp:.2f}
- Merchant proceeds (EUR): {merchant_proceeds_in_eur:.2f}
- Merchant proceeds (GBP): {merchant_proceeds_in_gbp:.2f}
- Top restaurant by revenue (EUR): {top_restaurant_by_revenue_eur}

## Assumptions

- Revenue KPIs only include payments with status `PAID`
- Currency conversion uses fixed project FX rates for deterministic offline execution
- The synthetic payment model assumes one payment record per booking
"""


# =========================
# WRITE REPORT
# =========================

report_path.write_text(
    content,
    encoding="utf-8",
)

print(f"Report written to: {report_path}")
