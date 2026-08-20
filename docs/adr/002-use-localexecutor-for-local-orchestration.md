# ADR-002: Use LocalExecutor for Local Orchestration

**Status:** Accepted  
**Date:** 2026-08-20

## Context

The platform currently contains a small pipeline with three sequential tasks:

generate raw data → dbt build → generate report

Distributed workers are not required for this workload.

Using CeleryExecutor would introduce additional infrastructure such as
Redis and Celery workers without providing meaningful benefits for the
current use case.

## Decision

Use Airflow LocalExecutor for local pipeline orchestration.

## Alternatives Considered

- CeleryExecutor
- KubernetesExecutor

## Consequences

### Benefits

- Simpler Airflow architecture
- No message broker required
- Supports parallel task execution when needed
- Appropriate for the current local workload

### Trade-offs

- Tasks execute within the Airflow runtime environment
- Not designed for independently scalable distributed workers