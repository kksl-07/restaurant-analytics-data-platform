from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

# =========================
# PATHS
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "raw"

BASE_PATH = Path(os.getenv("RAW_DATA_PATH", DEFAULT_DATA_PATH))

BASE_PATH.mkdir(parents=True, exist_ok=True)


# =========================
# CONFIG
# =========================

# Fixed seed for reproducible synthetic datasets
np.random.seed(42)

N_RESTAURANTS = 20
N_USERS = 100
N_BOOKINGS = 500


# =========================
# RESTAURANTS
# =========================

restaurants = pd.DataFrame(
    {
        "restaurant_id": [f"r{i}" for i in range(1, N_RESTAURANTS + 1)],
        "name": [f"Restaurant_{i}" for i in range(1, N_RESTAURANTS + 1)],
        "country": np.random.choice(
            ["IT", "FR", "DE", "ES"],
            N_RESTAURANTS,
        ),
        "city": np.random.choice(
            ["Milan", "Rome", "Paris", "Berlin", "Madrid"],
            N_RESTAURANTS,
        ),
        "cuisine_type": np.random.choice(
            ["Italian", "Japanese", "French", "Mexican"],
            N_RESTAURANTS,
        ),
        "price_range": np.random.choice(
            ["$", "$$", "$$$"],
            N_RESTAURANTS,
        ),
        "opened_date": (
            pd.to_datetime("2020-01-01")
            + pd.to_timedelta(
                np.random.randint(0, 1000, N_RESTAURANTS),
                unit="D",
            )
        ),
        "is_active": np.random.choice(
            [True, False],
            N_RESTAURANTS,
            p=[0.8, 0.2],
        ),
    }
)


# =========================
# USERS
# =========================

users = pd.DataFrame(
    {
        "user_id": [f"u{i}" for i in range(1, N_USERS + 1)],
        "created_at": (
            pd.to_datetime("2023-01-01")
            + pd.to_timedelta(
                np.random.randint(0, 365, N_USERS),
                unit="D",
            )
        ),
        "country": np.random.choice(
            ["IT", "FR", "DE", "ES"],
            N_USERS,
        ),
        "marketing_opt_in": np.random.choice(
            [True, False],
            N_USERS,
        ),
    }
)


# =========================
# BOOKINGS
# =========================

booking_ids = [f"b{i}" for i in range(1, N_BOOKINGS + 1)]

bookings = pd.DataFrame(
    {
        "booking_id": booking_ids,
        "created_at": (
            pd.to_datetime("2024-01-01")
            + pd.to_timedelta(
                np.random.randint(0, 90, N_BOOKINGS),
                unit="D",
            )
        ),
        "meal_at": (
            pd.to_datetime("2024-03-01")
            + pd.to_timedelta(
                np.random.randint(0, 90, N_BOOKINGS),
                unit="D",
            )
        ),
        "restaurant_id": np.random.choice(
            restaurants["restaurant_id"],
            N_BOOKINGS,
        ),
        "user_id": np.random.choice(
            users["user_id"],
            N_BOOKINGS,
        ),
        "party_size": np.random.randint(
            1,
            6,
            N_BOOKINGS,
        ),
        "status": np.random.choice(
            [
                "confirmed",
                "created",
                "fulfilled",
                "no_show",
                "cancelled",
            ],
            N_BOOKINGS,
            p=[0.5, 0.2, 0.1, 0.1, 0.1],
        ),
        "channel": np.random.choice(
            ["app", "web"],
            N_BOOKINGS,
        ),
    }
)


# =========================
# PAYMENTS
# =========================

# Simplification for this project:
# one payment record is generated for each booking.

currencies = np.random.choice(
    ["EUR", "GBP"],
    N_BOOKINGS,
    p=[0.75, 0.25],
)

payments = pd.DataFrame(
    {
        "payment_id": [f"p{i}" for i in range(1, N_BOOKINGS + 1)],
        "booking_id": bookings["booking_id"],
        "restaurant_id": bookings["restaurant_id"],
        "paid_at": (
            pd.to_datetime("2024-03-01")
            + pd.to_timedelta(
                np.random.randint(0, 30, N_BOOKINGS),
                unit="D",
            )
        ),
        "currency": currencies,
        "gross_amount": np.random.uniform(
            20,
            180,
            N_BOOKINGS,
        ).round(2),
        "platform_fee": np.random.uniform(
            2,
            18,
            N_BOOKINGS,
        ).round(2),
        "payment_status": np.random.choice(
            ["paid", "failed", "refunded"],
            N_BOOKINGS,
            p=[0.7, 0.2, 0.1],
        ),
    }
)


# =========================
# DATA QUALITY
# =========================

# Introduce a small number of null values to simulate
# imperfect real-world source data.

null_indexes = np.random.choice(
    bookings.index,
    10,
    replace=False,
)

bookings.loc[
    null_indexes,
    "party_size",
] = None


# =========================
# WRITE PARQUET
# =========================

datasets = {
    "restaurants": restaurants,
    "users": users,
    "bookings": bookings,
    "payments": payments,
}

for dataset_name, dataframe in datasets.items():
    output_path = BASE_PATH / f"{dataset_name}.parquet"

    dataframe.to_parquet(
        output_path,
        index=False,
    )

    print(f"Generated {output_path} ({len(dataframe)} rows)")


# =========================
# SUMMARY
# =========================

print("\nPayments currency distribution:")
print(payments["currency"].value_counts())

print("\nPayments status distribution:")
print(payments["payment_status"].value_counts())
