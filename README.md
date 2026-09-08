# 🍽️ Restaurant Analytics Data Platform

A reproducible end-to-end analytics data platform built with **Python, Parquet, DuckDB, dbt, Apache Airflow, Docker Compose, and GitHub Actions**.

The project simulates a restaurant marketplace analytics workflow, from deterministic synthetic source data generation to transformation, data quality validation, orchestration, analytics modeling, and downstream reporting.

The platform is intentionally small and self-contained. Its purpose is to demonstrate production-oriented Data Engineering practices without introducing infrastructure that is not required by the workload.

The core design focuses on:

- layered analytical modeling with dbt
- analytical processing with DuckDB
- deterministic synthetic source data
- data quality as a pipeline quality gate
- workflow orchestration with Apache Airflow
- reproducible local execution with Docker
- automated CI validation with GitHub Actions
- explicit architectural decisions and trade-offs

---

## 🏗️ Architecture

```text
                         ┌──────────────────────┐
                         │ Synthetic Data       │
                         │ Generator            │
                         │ Python               │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Raw Parquet          │
                         │                      │
                         │ restaurants          │
                         │ users                │
                         │ bookings             │
                         │ payments             │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ dbt + DuckDB         │
                         │                      │
                         │ staging              │
                         │ public               │
                         │ marts                │
                         │ data quality tests   │
                         └──────────┬───────────┘
                                    │
                              dbt build SUCCESS
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Validated Analytics  │
                         │ Mart in DuckDB       │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ generate_report.py   │
                         │                      │
                         │ consumer contract    │
                         │ validation           │
                         └──────────┬───────────┘
                                    │
                         ┌──────────┴───────────┐
                         ▼                      ▼
             restaurant_kpis.csv       summary_report.md
```

### Orchestration

Apache Airflow orchestrates the end-to-end analytics workflow:

```text
generate_raw_data
        │
        ▼
    dbt_build
        │
        ▼
 generate_report
```

`dbt_build` acts as the central quality gate.

If a dbt model or data quality test fails, the downstream reporting task is not executed.

### Continuous Integration

GitHub Actions independently validates the project on pull requests:

```text
Checkout repository
        │
        ▼
Python 3.12
        │
        ▼
Install dependencies
        │
        ▼
Ruff lint
        │
        ▼
Ruff format check
        │
        ▼
Generate synthetic data
        │
        ▼
Full dbt build
        │
        ▼
Models + data tests
```

---

## 🧰 Technology Stack

| Area | Technology |
|---|---|
| Language | Python 3.12 |
| Source format | Parquet |
| Data transformation | dbt |
| Analytical database | DuckDB |
| Data processing | pandas / PyArrow |
| Orchestration | Apache Airflow |
| Airflow executor | LocalExecutor |
| Airflow metadata database | PostgreSQL 16 |
| Containerization | Docker / Docker Compose |
| CI | GitHub Actions |
| Linting / formatting | Ruff |
| Data quality | dbt tests |
| Documentation | dbt docs |
| Outputs | CSV + Markdown |

---

## 📁 Project Structure

```text
restaurant-analytics-data-platform/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── airflow/
│   └── dags/
│       └── restaurant_analytics_pipeline.py
│
├── data/
│   └── raw/
│
├── models/
│   ├── staging/
│   ├── public/
│   ├── marts/
│   └── schema.yml
│
├── tests/
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
│
├── exports/
│   ├── cleaned/
│   ├── marts/
│   └── reports/
│
├── .duckdb/
├── logs/
├── target/
│
├── Dockerfile
├── docker-compose.yaml
├── Makefile
├── dbt_project.yml
├── requirements.txt
├── requirements-dev.txt
├── ruff.toml
└── README.md
```

Generated datasets, DuckDB databases, logs, dbt artifacts, and analytical outputs are excluded from version control where appropriate.

---

## 🚀 Quick Start

### Requirements

For the containerized execution path:

- Docker
- Docker Compose
- Make

Clone the repository:

```bash
git clone https://github.com/kksl-07/restaurant-analytics-data-platform.git
cd restaurant-analytics-data-platform
```

Run the standalone end-to-end pipeline:

```bash
make run
```

The pipeline generates the required source data, executes the dbt project and its tests, and generates the final analytical outputs.

---

## 🔄 Pipeline Execution

The standalone execution flow is:

```text
make run
    │
    ▼
Docker build
    │
    ▼
Check input datasets
    │
    ├── data exists ───────────────┐
    │                              │
    └── data missing               │
            │                      │
            ▼                      │
    generate_input_data.py         │
            │                      │
            ▼                      │
      Parquet datasets             │
            │                      │
            └──────────────────────┘
                       │
                       ▼
                   dbt build
                       │
             ┌─────────┼─────────┐
             ▼         ▼         ▼
          staging    public     marts
                       │
                       ▼
              data quality tests
                       │
                       ▼
              validated DuckDB mart
                       │
                       ▼
              generate_report.py
                 │             │
                 ▼             ▼
             mart CSV     summary report
```

`dbt build` is used instead of separate `dbt run` and `dbt test` commands so models and tests are executed according to the dbt dependency graph.

---

## 🌬️ Airflow Orchestration

The platform also provides an orchestrated execution path using Apache Airflow.

Start the Airflow environment with:

```bash
docker compose up -d
```

The main DAG is:

```text
restaurant_analytics_pipeline
```

It orchestrates:

```text
generate_raw_data
        │
        ▼
    dbt_build
        │
        ▼
 generate_report
```

Airflow uses `LocalExecutor`, while PostgreSQL 16 is used exclusively as the Airflow metadata database.

DuckDB remains the analytical database used by the data platform.

### Quality Gate

The dependency between `dbt_build` and `generate_report` is intentional.

```text
dbt build
   │
   ├── SUCCESS ──→ generate_report
   │
   └── FAILURE ──→ pipeline stops
```

This ensures that downstream reporting artifacts cannot be generated from models that failed transformation or data quality validation.

---

## 🧪 Synthetic Data

The project does not require external datasets.

Synthetic input data can be generated with:

```bash
make generate-data
```

The generator creates:

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

A fixed random seed is used so the generated data is deterministic across executions.

The generated data intentionally contains a small amount of imperfect data to exercise validation logic in the transformation layer.

---

## 🧱 Data Modeling

The dbt project follows three analytical layers:

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

The mart is materialized in DuckDB and validated as part of `dbt build`.

After the dbt quality gate succeeds, the reporting layer reads the validated mart from DuckDB and publishes it to:

```text
exports/marts/restaurant_kpis.csv
```

This separation ensures that downstream reporting artifacts are generated only from a mart that has successfully passed transformation and data quality validation.

---

## 📊 Booking KPIs

### `total_bookings`

Total number of valid bookings associated with the restaurant.

### `confirmed_or_fulfilled_bookings`

Number of bookings whose current lifecycle status is either:

```text
CONFIRMED
FULFILLED
```

### `booking_cancellation_rate`

Share of valid bookings for the restaurant whose lifecycle status is:

```text
CANCELLED
```

The metric is represented as a ratio between `0` and `1`.

Because the mart grain is one row per restaurant, averaging this column across restaurants produces an unweighted average of restaurant-level cancellation rates rather than the global platform cancellation rate.

### `no_show_rate`

Share of valid bookings for the restaurant whose lifecycle status is:

```text
NO_SHOW
```

The same grain consideration applies when aggregating this rate across restaurants.

### `booked_covers`

Total party size across all valid bookings.

### `fulfilled_covers`

Total party size associated with bookings whose lifecycle status is:

```text
FULFILLED
```

### `unique_bookers`

Number of distinct users associated with valid bookings for the restaurant.

This metric is calculated at restaurant grain and should not be summed across restaurants to derive a platform-wide unique-user count because the same user may book at multiple restaurants.

---

## 💳 Payment KPIs

### `paid_bookings`

Number of bookings associated with a `PAID` payment.

### `paid_bookings_eur` / `paid_bookings_gbp`

Paid bookings split by original payment currency.

---

## 💰 Revenue KPIs

### `gross_revenue_eur` / `gross_revenue_gbp`

Gross value of `PAID` transactions in their original currency.

### `platform_fee_eur` / `platform_fee_gbp`

Platform fees generated by `PAID` transactions in their original currency.

### `total_gross_revenue_in_eur`

Total gross value of all `PAID` transactions normalized to EUR using the fixed project FX rate.

### `total_gross_revenue_in_gbp`

Total gross value of all `PAID` transactions normalized to GBP using the fixed project FX rate.

### `total_platform_fee_in_eur` / `total_platform_fee_in_gbp`

Total platform fees generated by `PAID` transactions normalized to EUR and GBP.

### `merchant_proceeds_in_eur` / `merchant_proceeds_in_gbp`

Amount payable to restaurants after deducting the platform fee from `PAID` transactions, normalized to EUR and GBP.

The financial relationship is:

```text
gross transaction value
=
platform fee
+
merchant proceeds
```

### `avg_paid_booking_value_in_eur` / `avg_paid_booking_value_in_gbp`

Average gross value of a paid booking after normalizing transactions to EUR or GBP.

---

## 📌 Data Assumptions

### Active Restaurants

Only restaurants where:

```sql
is_active = true
```

are exposed by `pub_restaurants` and therefore included in downstream analytics.

Filtering inactive restaurants keeps the analytical mart focused on the currently active restaurant portfolio.

The trade-off is that historical activity associated exclusively with restaurants that are now inactive is not represented in the final restaurant KPI mart.

### Booking Validation

The public booking layer accepts:

```text
CANCELLED
CONFIRMED
CREATED
FULFILLED
NO_SHOW
```

Bookings must also contain valid restaurant and user identifiers and a valid positive party size before being exposed downstream.

### Payments Logic

Revenue KPIs only include payments where:

```text
payment_status = 'PAID'
```

The synthetic dataset assumes:

```text
one payment record per booking
```

This is an intentional simplification.

A real payment system could contain multiple payment attempts and lifecycle events:

```text
booking
   │
   ├── FAILED
   ├── PAID
   └── REFUNDED
```

Payment data would therefore need to be resolved to the appropriate analytical grain before joining it with bookings.

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

This intentionally provides:

- deterministic results
- reproducible pipeline executions
- fully offline processing

In a production environment, FX rates would typically be sourced from a dedicated exchange-rate dataset or external provider and applied according to transaction date.

---

## 🧪 Data Quality

The project uses both dbt schema tests and custom business invariant tests.

Run the complete test suite with:

```bash
make test
```

### Schema Tests

Standard dbt tests include:

```text
not_null
unique
accepted_values
```

These validate identifiers, required fields, booking statuses, payment statuses, and supported currencies.

### Business Invariant Tests

#### Non-negative payment amounts

```text
tests/assert_payment_amounts_non_negative.sql
```

Validates:

```text
gross_amount >= 0
platform_fee >= 0
```

#### Valid booking rates

```text
tests/assert_booking_rates_valid.sql
```

Validates:

```text
0 <= booking_cancellation_rate <= 1
0 <= no_show_rate <= 1
```

#### Financial reconciliation

```text
tests/assert_merchant_proceeds_consistent.sql
```

Validates:

```text
gross revenue
≈
platform fee + merchant proceeds
```

A small tolerance is allowed because financial metrics are rounded to two decimal places in the analytical mart.

These tests are executed as part of `dbt build`.

In the Airflow DAG, `dbt_build` acts as the pipeline quality gate: if a model or data test fails, `generate_report` is not executed.

---

## 📄 Reporting and Consumer Contract

`generate_report.py` acts as a downstream consumer of the validated analytical mart.

It reads:

```text
main.mart_restaurant_kpis
```

directly from DuckDB.

Before producing downstream artifacts, the reporting layer validates a minimum required schema through its consumer data contract.

The contract defines the columns required by the reporting consumer without restricting the complete schema exposed by the mart.

Conceptually:

```text
dbt mart schema
      │
      ├── required reporting columns
      │       ↓
      │   consumer contract
      │       ↓
      │   report generation
      │
      └── additional columns
              ↓
         preserved in CSV export
```

If a required column is missing, report generation fails rather than silently producing incomplete output.

---

## 📦 Outputs

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

---

## 📘 dbt Documentation

Generate and serve dbt documentation with:

```bash
make docs
```

dbt documentation provides:

- model lineage
- DAG visualization
- model descriptions
- column descriptions
- associated data tests

> Note: verify the local documentation port before running dbt docs alongside the Airflow UI, as both services may otherwise be configured to use the same host port.

---

## 🛠️ Make Commands

### Run the complete standalone pipeline

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

A local reproducibility check can therefore begin with:

```bash
make clean-all
make run
```

---

## 🔄 Continuous Integration

GitHub Actions validates pull requests targeting `main` and pushes to `main`.

The CI pipeline performs:

```text
Checkout
   ↓
Python 3.12
   ↓
Install runtime dependencies
   ↓
Install development dependencies
   ↓
ruff check .
   ↓
ruff format --check .
   ↓
generate_input_data.py
   ↓
full dbt build
   ↓
models + tests
```

The CI intentionally performs a full `dbt build` instead of state-based selection.

The project is currently small enough that a full build is inexpensive and provides a stronger reproducibility check against a fresh CI environment.

State-based or slim CI execution can be introduced if the project grows enough to justify the additional complexity.

---

## 🌿 Development Workflow

Changes are developed on dedicated branches and integrated into `main` through pull requests.

```text
main
  │
  ▼
feature / docs branch
  │
  ▼
development
  │
  ▼
local validation
  │
  ▼
pull request
  │
  ▼
GitHub Actions
  │
  ▼
required status checks
  │
  ▼
merge to protected main
```

The `main` branch is protected by a GitHub ruleset.

The workflow requires the CI quality gate to pass before changes can be merged and protects the branch against unsafe history changes.

---

## ⚙️ Execution Model

The platform provides two local execution paths.

### Standalone Execution

The Make/Docker workflow provides a lightweight way to execute the complete analytics pipeline without manually installing project runtime dependencies on the host.

### Orchestrated Execution

Apache Airflow runs locally through Docker Compose and orchestrates the same analytics workflow.

Airflow uses:

```text
LocalExecutor
PostgreSQL 16 → Airflow metadata
DuckDB       → analytical data
```

Keeping the orchestration metadata database separate from the analytical database makes the responsibilities of the two systems explicit.

The current implementation prioritizes portability, reproducibility, and architectural clarity over distributed execution.

---

## ⚖️ Design Decisions and Trade-offs

### DuckDB

DuckDB provides a lightweight analytical engine with native Parquet support and makes the project easy to execute locally.

For a production-scale platform, the analytical engine could be replaced by a cloud data warehouse such as Snowflake, BigQuery, or Amazon Redshift without fundamentally changing the dbt modeling approach.

### Parquet Sources

Parquet provides a columnar input format suitable for analytical workloads and can be queried efficiently by DuckDB.

Production sources could instead arrive from object storage, operational databases, APIs, streaming systems, or ingestion services.

### Airflow LocalExecutor

LocalExecutor is sufficient for the current workload and keeps the local architecture simple.

Distributed workers, Celery, Redis, or Kubernetes-based task execution would add operational complexity without providing meaningful value at the current project scale.

### dbt Build as a Quality Gate

`dbt build` combines transformation and validation according to the dbt dependency graph.

The reporting layer is downstream of this gate and therefore cannot execute successfully when the analytical models fail validation.

### Fixed FX Rates

Static exchange rates improve reproducibility but do not model historical currency movements.

A production implementation would maintain an FX-rate dataset and resolve the appropriate rate according to transaction date.

### Single Payment per Booking

The synthetic model intentionally keeps the payment relationship simple.

A real payment system would require explicit handling of payment attempts, refunds, reversals, and potentially partial payments.

### Local Execution

The current implementation prioritizes portability and reproducibility over distributed execution.

The transformation and orchestration patterns can be extended toward cloud infrastructure as data volume and operational requirements increase.

---

## 🔮 Future Roadmap

The Data Platform Core intentionally stops at a stable local analytics platform rather than continuously adding infrastructure.

Potential platform extensions include:

- incremental dbt models and state-based execution
- source freshness checks
- richer synthetic data volumes
- payment event modeling
- historical FX-rate modeling
- data observability and alerting
- cloud object storage
- cloud data warehouse deployment
- isolated or distributed Airflow task execution

Before extending the platform with an AI layer, the next development phase focuses on a separate **Software Engineering learning roadmap**.

Potential later AI extensions include:

```text
dbt metadata / documentation
          ↓
      retrieval / RAG
          ↓
      Text-to-SQL
          ↓
Analytics Data Agent
```

These extensions are intentionally outside the scope of the current Data Platform Core.

---

## 🎯 Project Goals

This project demonstrates:

- layered analytical data modeling
- reproducible data pipelines
- workflow orchestration
- containerized local execution
- data quality engineering
- CI-based quality gates
- explicit business rules
- analytical grain management
- financial metric reconciliation
- consumer-side schema contracts
- documentation and lineage
- engineering trade-off analysis

The emphasis is not only on producing analytical outputs, but on building a small data platform whose behavior is **understandable, testable, reproducible, and extensible**.