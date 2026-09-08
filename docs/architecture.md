# Architecture

## Overview

Restaurant Analytics Data Platform is a small, self-contained analytics
platform designed to demonstrate production-oriented data engineering
patterns in a reproducible local environment.

The architecture separates five main concerns:

1. source data generation
2. analytical transformation
3. data quality validation
4. workflow orchestration
5. downstream reporting

DuckDB is the analytical database, dbt owns transformation and business
modeling, Apache Airflow orchestrates the workflow, and GitHub Actions
provides an independent CI quality gate.

---

## High-Level Architecture

```text
                         ┌──────────────────────┐
                         │ Synthetic Data       │
                         │ Generator            │
                         │                      │
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
                         │ tests                │
                         └──────────┬───────────┘
                                    │
                              dbt build SUCCESS
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Validated Analytics  │
                         │ Mart                 │
                         │                      │
                         │ DuckDB               │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Reporting Consumer   │
                         │                      │
                         │ generate_report.py   │
                         │ contract validation  │
                         └──────────┬───────────┘
                                    │
                         ┌──────────┴───────────┐
                         │                      │
                         ▼                      ▼
               restaurant_kpis.csv     summary_report.md
```

---

## Data Flow

### 1. Source Generation

`scripts/generate_input_data.py` generates deterministic synthetic source
data representing:

- restaurants
- users
- bookings
- payments

The datasets are stored as Parquet files under:

```text
data/raw/
```

A fixed random seed makes the generated datasets reproducible.

The generator also introduces a small amount of intentionally imperfect
data so that validation behavior can be exercised by the transformation
layer.

---

### 2. Transformation Layer

dbt owns the transformation logic and analytical business rules.

The model hierarchy is:

```text
Raw Parquet
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

#### Staging

The staging layer performs technical normalization while preserving
source-level semantics.

Typical responsibilities include:

- type normalization
- naming normalization
- string cleanup
- timestamp normalization
- status normalization
- currency normalization

#### Public

The public layer exposes cleaned and validated datasets suitable for
downstream analytical use.

It applies business validation such as:

- valid identifiers
- valid booking statuses
- valid payment statuses
- supported currencies
- valid monetary values

#### Marts

The mart layer owns analytical aggregation and KPI definitions.

The primary analytical mart is:

```text
mart_restaurant_kpis
```

with grain:

```text
one row per active restaurant
```

Business KPI definitions remain in dbt rather than being reimplemented
inside the reporting layer.

---

## Analytical Storage

DuckDB is the analytical database for the platform.

It stores the relations produced by dbt and provides the validated
analytical mart consumed by the reporting layer.

DuckDB was selected because the current workload:

- fits comfortably on a single machine
- is analytical rather than transactional
- benefits from native Parquet support
- does not require distributed computation
- should remain simple to reproduce locally

The architecture does not depend on DuckDB-specific business modeling.
The dbt modeling approach could later be adapted to a cloud analytical
warehouse if the workload required it.

---

## Data Quality Gate

The platform uses:

```text
dbt build
```

as the central transformation and data quality gate.

`dbt build` executes models and tests according to the dbt dependency
graph.

Conceptually:

```text
Raw Data
   │
   ▼
Transformations
   │
   ▼
dbt Tests
   │
   ├── FAILURE ──→ pipeline stops
   │
   └── SUCCESS
          │
          ▼
    Validated Mart
          │
          ▼
      Reporting
```

This prevents downstream reporting artifacts from being generated when
the analytical model has failed transformation or data quality checks.

Data quality includes both standard dbt schema tests and custom business
invariant tests.

---

## Reporting Layer

`scripts/generate_report.py` is a downstream consumer of the validated
analytics layer.

It does not redefine the business KPIs owned by dbt.

Instead, it:

1. connects to DuckDB in read-only mode
2. reads `main.mart_restaurant_kpis`
3. validates the reporting consumer contract
4. exports the complete validated mart
5. calculates report-level aggregations
6. generates the Markdown summary report

The final artifacts are:

```text
exports/marts/restaurant_kpis.csv
exports/reports/summary_report.md
```

---

## Consumer Data Contract

The reporting layer defines a minimum schema required to consume
`mart_restaurant_kpis`.

Conceptually:

```text
                 mart_restaurant_kpis
                          │
             ┌────────────┴────────────┐
             │                         │
             ▼                         ▼
    required columns             extra columns
             │                         │
             ▼                         │
    contract validation                │
             │                         │
             └────────────┬────────────┘
                          ▼
                    complete export
```

The contract therefore represents a **minimum required schema**, not the
complete mart schema.

Adding a new column to the mart does not break the reporting consumer.

Removing or renaming a required column causes report generation to fail
explicitly.

This provides a simple form of producer-consumer compatibility checking
between the dbt mart and the reporting layer.

---

## Airflow Orchestration

Apache Airflow orchestrates the complete workflow.

The DAG is:

```text
restaurant_analytics_pipeline
```

with the dependency graph:

```text
generate_raw_data
        │
        ▼
    dbt_build
        │
        ▼
 generate_report
```

The ordering is intentional.

`generate_report` depends on a successful `dbt_build`, so Airflow's task
dependency and failure propagation enforce the data quality gate.

If `dbt_build` fails:

```text
generate_raw_data   SUCCESS
        │
        ▼
    dbt_build       FAILED
        │
        ▼
 generate_report    NOT EXECUTED
```

### Airflow Runtime

The local Airflow environment runs through Docker Compose.

Airflow uses:

```text
LocalExecutor
```

and PostgreSQL 16 as its metadata database.

The responsibilities of the two databases are intentionally separate:

```text
PostgreSQL
    │
    └── Airflow metadata
        DAG runs
        task instances
        scheduler state

DuckDB
    │
    └── analytical data
        dbt models
        analytics mart
```

PostgreSQL is therefore infrastructure for orchestration and is not part
of the analytical data model.

---

## Execution Models

The platform provides two local execution paths.

### Standalone

```text
make run
```

provides a lightweight end-to-end execution path.

It is useful for:

- local development
- validating the analytical pipeline
- reproducing the complete data flow without the orchestrator

### Orchestrated

```text
docker compose up -d
```

starts the Airflow environment.

The Airflow DAG provides:

- explicit task dependencies
- execution history
- task-level failure visibility
- orchestration semantics
- quality-gate enforcement

Both execution paths ultimately exercise the same core analytical
components.

---

## Continuous Integration

GitHub Actions provides an independent validation path for repository
changes.

The CI workflow executes:

```text
Checkout
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

The CI starts from a fresh environment and therefore also acts as a
reproducibility check for the analytical core.

A full `dbt build` is intentionally used instead of state-based
selection because the current project is small enough that the simpler
and stronger full-project validation is preferable.

---

## Repository Quality Gate

The repository uses two complementary mechanisms:

```text
GitHub Actions
      │
      └── determines whether the project is valid
                  │
                  ▼
           Validate project
                  │
                  ▼
GitHub Ruleset
      │
      └── determines whether the result is required
                  │
                  ▼
               main
```

Changes are developed on dedicated branches and integrated through pull
requests.

The protected `main` branch requires the CI quality gate before changes
can be merged.

---

## Architectural Principles

The current architecture follows a few deliberate principles.

### Keep business logic in the transformation layer

dbt owns analytical definitions and KPI calculations.

Python reporting code consumes those results rather than becoming a
second transformation layer.

### Fail before publishing

Reporting is downstream of transformation and data quality validation.

Invalid analytical models should fail explicitly instead of producing
apparently successful downstream artifacts.

### Prefer reproducibility over unnecessary infrastructure

The workload does not require a distributed processing engine or cloud
warehouse.

DuckDB, Parquet, and local containers provide enough infrastructure to
demonstrate the relevant engineering patterns.

### Separate orchestration from analytics

Airflow coordinates work.

DuckDB processes and stores analytical data.

PostgreSQL stores Airflow operational metadata.

Each component therefore has a clear responsibility.

### Automate validation

Local Ruff checks, dbt tests, GitHub Actions, and protected-branch rules
reduce the chance of integrating invalid changes into `main`.

---

## Current Boundaries

The Data Platform Core intentionally does not implement:

- distributed data processing
- cloud infrastructure
- real-time streaming
- incremental dbt execution
- production observability and alerting
- historical FX-rate ingestion
- complex payment-event modeling
- AI or agent functionality

These are potential extensions rather than requirements for the current
workload.

The goal of the current architecture is to provide a small but
well-structured baseline that is understandable, reproducible,
testable, and extensible.