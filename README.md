# 🍽️ Restaurant Analytics Data Platform

A reproducible end-to-end analytics data platform built with **Docker**, **dbt**, **DuckDB**, and **Python**.

The project simulates a restaurant marketplace analytics workflow, from synthetic source data generation and data transformation to data quality validation, KPI modeling, exports, and report generation.

The goal is to demonstrate how a small analytics platform can be designed with clear data layers, reproducible execution, explicit business rules, automated testing, and documented architectural trade-offs.

---

## 🏗️ Architecture

```text
                         ┌─────────────────────┐
                         │   Synthetic Data    │
                         │      Generator      │
                         │      (Python)       │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    Raw Parquet      │
                         │                     │
                         │ restaurants         │
                         │ users               │
                         │ bookings            │
                         │ payments            │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    dbt Staging      │
                         │                     │
                         │ type normalization  │
                         │ naming cleanup      │
                         │ basic standardization│
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    dbt Public       │
                         │                     │
                         │ validation          │
                         │ business filtering  │
                         │ cleaned datasets    │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      dbt Mart       │
                         │                     │
                         │ restaurant KPIs     │
                         │ booking metrics     │
                         │ revenue metrics     │
                         └──────────┬──────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     │                             │
                     ▼                             ▼
            ┌─────────────────┐          ┌─────────────────┐
            │   CSV Exports   │          │  Data Quality   │
            │                 │          │     Tests       │
            └────────┬────────┘          └─────────────────┘
                     │
                     ▼
            ┌─────────────────┐
            │ Summary Report  │
            │    (Python)     │
            └─────────────────┘
```

The complete platform runs locally inside Docker and does not require external infrastructure or data services.

---

## 🧰 Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.12 |
| Transformation | dbt |
| Analytical engine | DuckDB |
| Source format | Parquet |
| Data processing | pandas / PyArrow |
| Containerization | Docker |
| Automation | Make |
| Data quality | dbt tests |
| Documentation | dbt docs |
| Output | CSV + Markdown |

---

## 📁 Project Structure

```text
restaurant-analytics-data-platform/
│
├── data/
│   ├── raw/
│   ├── generated/
│   └── sample/
│
├── models/
│   ├── staging/
│   │   ├── stg_restaurants.sql
│   │   ├── stg_users.sql
│   │   ├── stg_bookings.sql
│   │   └── stg_payments.sql
│   │
│   ├── public/
│   │   ├── pub_restaurants.sql
│   │   ├── pub_users.sql
│   │   ├── pub_bookings.sql
│   │   └── pub_payments.sql
│   │
│   ├── marts/
│   │   └── mart_restaurant_kpis.sql
│   │
│   └── schema.yml
│
├── tests/
│   ├── assert_payment_amounts_non_negative.sql
│   ├── assert_booking_rates_valid.sql
│   └── assert_merchant_proceeds_consistent.sql
│
├── scripts/
│   ├── generate_input_data.py
│   ├── generate_report.py
│   ├── run.sh
│   └── test.sh
│
├── profiles/
│   └── profiles.yml
│
├── docs/
│   └── architecture.md
│
├── exports/
│   ├── cleaned/
│   ├── marts/
│   └── reports/
│
├── logs/
├── .duckdb/
├── macros/
│
├── Dockerfile
├── Makefile
├── requirements.txt
├── dbt_project.yml
└── README.md
```

Generated datasets, DuckDB databases, logs, dbt artifacts, and analytical outputs are excluded from version control where appropriate.

---

## 🚀 Quick Start

### Requirements

The only runtime requirement is:

- Docker

Clone the repository and enter the project directory:

```bash
git clone <repository-url>
cd restaurant-analytics-data-platform
```

Run the complete pipeline:

```bash
make run
```

The command builds the Docker image, checks the source data, generates synthetic data when required, runs the dbt project and its tests, exports the analytical datasets, and generates the final summary report.

---

## 🔄 Pipeline Execution

The end-to-end execution flow is:

```text
make run
    │
    ▼
Docker build
    │
    ▼
Check input datasets
    │
    ├── data exists ──────────────────┐
    │                                 │
    └── data missing                  │
            │                         │
            ▼                         │
    generate_input_data.py            │
            │                         │
            ▼                         │
      Parquet datasets                │
            │                         │
            └─────────────────────────┘
                       │
                       ▼
                   dbt build
                       │
             ┌─────────┼─────────┐
             ▼         ▼         ▼
          staging    public     marts
                                  │
                                  ▼
                         Data quality tests
                                  │
                                  ▼
                              CSV exports
                                  │
                                  ▼
                         generate_report.py
                                  │
                                  ▼
                         summary_report.md
```

`dbt build` is used instead of separate `dbt run` and `dbt test` commands so that models and tests are executed according to the dbt dependency graph.

---

## 🧪 Synthetic Data

The project does not require external datasets.

Synthetic input data can be generated with:

```bash
make generate-data
```

The generator creates four source datasets:

| Dataset | Description |
|---|---|
| `restaurants.parquet` | Restaurant master data |
| `users.parquet` | User profiles |
| `bookings.parquet` | Booking activity |
| `payments.parquet` | Payment activity |

The default dataset contains:

```text
20 restaurants
100 users
500 bookings
500 payments
```

A fixed random seed is used so that the generated data is deterministic across executions.

The generated data intentionally contains a small amount of imperfect data to exercise validation logic in the transformation layer.

---

## 🧱 Data Modeling

The dbt project follows three main layers:

```text
raw
 │
 ▼
staging
 │
 ▼
public
 │
 ▼
marts
```

### Staging Layer

The staging layer performs technical normalization while preserving source-level semantics.

Responsibilities include:

- explicit type casting
- column renaming
- string trimming
- status normalization
- currency normalization
- timestamp normalization

Models:

```text
stg_restaurants
stg_users
stg_bookings
stg_payments
```

---

### Public Layer

The public layer exposes validated datasets suitable for downstream analytical consumption.

Responsibilities include:

- removing invalid identifiers
- validating business fields
- filtering unsupported values
- enforcing valid booking statuses
- enforcing valid payment statuses
- enforcing supported currencies
- removing invalid monetary amounts

Models:

```text
pub_restaurants
pub_users
pub_bookings
pub_payments
```

Cleaned versions of these datasets are exported to:

```text
exports/cleaned/
```

---

### Mart Layer

The final analytical model is:

```text
mart_restaurant_kpis
```

Its grain is:

```text
one row per active restaurant
```

It combines restaurant, booking, user, and payment information to expose operational and financial KPIs.

The mart is exported to:

```text
exports/marts/restaurant_kpis.csv
```

---

## 📊 Booking KPIs

### total_bookings

Total number of valid bookings associated with the restaurant.

### confirmed_or_fulfilled_bookings

Number of bookings whose current lifecycle status is either:

```text
CONFIRMED
FULFILLED
```

### booking_cancellation_rate

Share of valid bookings whose current lifecycle status is:

```text
CANCELLED
```

The metric is represented as a ratio between `0` and `1`.

### no_show_rate

Share of valid bookings whose current lifecycle status is:

```text
NO_SHOW
```

### booked_covers

Total party size across all valid bookings.

### fulfilled_covers

Total party size associated only with bookings whose current lifecycle status is:

```text
FULFILLED
```

### unique_bookers

Number of distinct users associated with valid bookings for the restaurant.

---

## 💳 Payment KPIs

### paid_bookings

Number of bookings associated with a `PAID` payment.

### paid_bookings_eur / paid_bookings_gbp

Paid bookings split by the original payment currency.

---

## 💰 Revenue KPIs

### gross_revenue_eur / gross_revenue_gbp

Gross value of `PAID` transactions in their original currency.

### platform_fee_eur / platform_fee_gbp

Platform fees generated by `PAID` transactions in their original currency.

### total_gross_revenue_in_eur

Total gross value of all `PAID` transactions normalized to EUR using the fixed project FX rate.

### total_gross_revenue_in_gbp

Total gross value of all `PAID` transactions normalized to GBP using the fixed project FX rate.

### total_platform_fee_in_eur / total_platform_fee_in_gbp

Total platform fees generated by `PAID` transactions, normalized to EUR and GBP.

### merchant_proceeds_in_eur / merchant_proceeds_in_gbp

Amount payable to restaurants after deducting the platform fee from `PAID` transactions, normalized to EUR and GBP.

The financial relationship is:

```text
gross transaction value
=
platform fee
+
merchant proceeds
```

### avg_paid_booking_value_in_eur / avg_paid_booking_value_in_gbp

Average gross value of a paid booking after normalizing transactions to EUR or GBP.

---

## 📌 Data Assumptions

### Active Restaurants

Only restaurants where:

```sql
is_active = true
```

are exposed by `pub_restaurants` and therefore included in downstream analytics.

**Tradeoff**

Filtering inactive restaurants keeps the analytical mart focused on the currently active restaurant portfolio.

As a consequence, historical activity associated exclusively with restaurants that are now inactive is not represented in the final restaurant KPI mart.

---

### Booking Validation

The public booking layer accepts the following lifecycle statuses:

```text
CANCELLED
CONFIRMED
CREATED
FULFILLED
NO_SHOW
```

Bookings must also contain valid restaurant and user identifiers and a valid positive party size before being exposed downstream.

---

### Payments Logic

Revenue KPIs only include payments with:

```text
payment_status = 'PAID'
```

The synthetic dataset assumes:

```text
one payment record per booking
```

This is an intentional simplification.

In a production payment system, a booking could generate multiple payment events or attempts, for example:

```text
booking
   │
   ├── FAILED
   ├── PAID
   └── REFUNDED
```

Payment data would therefore need to be resolved to the appropriate analytical grain before joining it with bookings.

---

### Currency Handling

The project supports:

```text
EUR
GBP
```

Fixed FX rates are used:

```text
1 GBP = 1.17 EUR
1 EUR = 0.8547 GBP
```

This design intentionally provides:

- deterministic results
- reproducible pipeline executions
- fully offline processing

In a production environment, FX rates would typically be sourced from a dedicated exchange-rate dataset or external provider and applied according to the relevant transaction date.

---

## 🧪 Data Quality

The project uses both dbt schema tests and custom business invariant tests.

Run the complete test suite with:

```bash
make test
```

### Schema Tests

The project uses standard dbt tests including:

```text
not_null
unique
accepted_values
```

These validate identifiers, required fields, booking statuses, payment statuses, and supported currencies.

### Business Invariant Tests

The project also contains custom singular tests.

#### Non-negative payment amounts

```text
tests/assert_payment_amounts_non_negative.sql
```

Validates that:

```text
gross_amount >= 0
platform_fee >= 0
```

for payments exposed by the public layer.

#### Valid booking rates

```text
tests/assert_booking_rates_valid.sql
```

Ensures that:

```text
0 <= booking_cancellation_rate <= 1
0 <= no_show_rate <= 1
```

#### Financial reconciliation

```text
tests/assert_merchant_proceeds_consistent.sql
```

Validates the invariant:

```text
gross revenue
≈
platform fee + merchant proceeds
```

A small tolerance is allowed because financial metrics are rounded to two decimal places in the analytical mart.

These tests are also executed during:

```bash
make run
```

because the end-to-end pipeline uses `dbt build`.

---

## 📄 Outputs

A successful execution produces three categories of artifacts.

### Cleaned Data

```text
exports/cleaned/
├── restaurants_clean.csv
├── users_clean.csv
├── bookings_clean.csv
└── payments_clean.csv
```

### Analytical Mart

```text
exports/marts/restaurant_kpis.csv
```

### Summary Report

```text
exports/reports/summary_report.md
```

The summary report contains operational and financial metrics derived from the final analytical mart.

---

## 📘 dbt Documentation

Generate and serve the dbt documentation with:

```bash
make docs
```

The generated documentation provides:

- model lineage
- DAG visualization
- model descriptions
- column descriptions
- associated data tests

The documentation is served locally on:

```text
http://localhost:8080
```

---

## 🛠️ Make Commands

### Run the complete pipeline

```bash
make run
```

### Generate synthetic data

```bash
make generate-data
```

### Run tests

```bash
make test
```

### Generate and serve dbt documentation

```bash
make docs
```

### Remove generated analytical artifacts

```bash
make clean
```

### Remove all generated artifacts including raw datasets

```bash
make clean-all
```

A full reproducibility test can therefore be performed with:

```bash
make clean-all
make run
```

---

## ⚙️ Execution Model

The platform is designed to be:

- deterministic
- reproducible
- containerized
- fully local
- independent from external data services

Docker provides the execution environment while DuckDB acts as the local analytical engine.

This makes it possible to reproduce the complete pipeline without installing dbt, DuckDB, or project-specific Python dependencies directly on the host machine.

---

## ⚖️ Design Decisions and Trade-offs

### DuckDB

DuckDB provides a lightweight analytical engine with native Parquet support and makes the project easy to execute locally.

For a production-scale platform, the analytical engine could be replaced by a cloud data warehouse such as Snowflake, BigQuery, or Amazon Redshift without fundamentally changing the dbt modeling approach.

### Parquet Sources

Parquet provides a columnar input format suitable for analytical workloads and can be queried directly by DuckDB.

In a production environment, source data could instead arrive from object storage, operational databases, APIs, streaming systems, or ingestion services.

### Fixed FX Rates

Static exchange rates improve reproducibility but do not model historical currency movements.

A production implementation would maintain an FX-rate dimension and resolve the appropriate rate according to the transaction date.

### Single Payment per Booking

The synthetic model intentionally keeps the payment relationship simple.

A real payment system would require explicit handling of payment attempts, refunds, reversals, and potentially partial payments.

### Local Execution

The current implementation prioritizes portability and reproducibility over distributed execution.

The transformation and orchestration patterns can be extended toward cloud infrastructure as data volume and operational requirements increase.

---

## 🔮 Possible Extensions

Potential next steps include:

- Airflow orchestration
- incremental dbt models
- source freshness checks
- CI/CD with GitHub Actions
- automated linting
- data contracts
- richer synthetic data volumes
- payment event modeling
- historical FX rates
- cloud object storage
- cloud data warehouse deployment
- observability and alerting

---

## 🎯 Project Goals

This project focuses on demonstrating:

- layered analytical data modeling
- reproducible data pipelines
- containerized execution
- data quality engineering
- explicit business rules
- analytical grain management
- financial metric reconciliation
- documentation and lineage
- engineering trade-off analysis

The emphasis is not only on producing analytical outputs, but on building a small data platform whose behavior is **understandable, testable, reproducible, and extensible**.