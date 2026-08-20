# ADR-003: Use a Custom Airflow Runtime Image

**Status:** Accepted  
**Date:** 2026-08-20

## Context

Airflow needs to execute Python scripts and dbt commands used by the analytics
platform.

The standard Airflow image does not contain the project's analytics
dependencies such as dbt-duckdb, DuckDB, pandas, and PyArrow.

Two approaches were considered:

1. Include the analytics runtime inside the Airflow image.
2. Keep Airflow as a pure orchestrator and execute pipeline tasks in separate
   workload containers.

The current pipeline uses a small and homogeneous Python/dbt runtime.

## Decision

Build a custom Airflow image based on the official Airflow image and install
the existing project dependencies into it.

Airflow tasks will execute directly inside this runtime.

## Alternatives Considered

Use Airflow only as an orchestrator and execute each workload in separate
Docker containers.

## Consequences

### Benefits

- Simple local architecture
- Python and dbt commands are directly available to Airflow tasks
- Reuses the existing project dependencies
- Avoids additional container orchestration

### Trade-offs

- Airflow and the analytics runtime are coupled
- The Airflow image becomes larger
- Less suitable for heterogeneous workloads requiring different runtimes

For a larger platform, separating orchestration from workload execution would
likely provide better isolation and independent scalability.