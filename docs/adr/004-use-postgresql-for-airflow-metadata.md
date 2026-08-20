# ADR-004: Use PostgreSQL for Airflow Metadata

**Status:** Accepted  
**Date:** 2026-08-20

## Context

Airflow requires a metadata database to persist operational information such
as DAG runs, task instances, and scheduler state.

The analytics platform already uses DuckDB, but DuckDB serves a different
purpose: it stores and processes analytical data.

Using the same database conceptually for both responsibilities would couple
Airflow operational metadata with analytical data.

## Decision

Use PostgreSQL as the Airflow metadata database and keep DuckDB exclusively
for analytics workloads.

## Consequences

This creates a clear separation of responsibilities:

- PostgreSQL → Airflow operational metadata
- DuckDB → restaurant analytics data

The trade-off is an additional local service, managed through Docker Compose.