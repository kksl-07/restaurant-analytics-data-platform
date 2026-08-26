# ADR-001: Use Docker Compose for Local Airflow

**Status:** Accepted  
**Date:** 2026-08-20

## Context

The analytics platform already uses Docker to provide a reproducible local
runtime.

Introducing Airflow directly into the host Python environment would add
Airflow and its dependencies to the developer machine and make the local
setup harder to reproduce.

The Airflow environment also requires multiple services, including the
scheduler, API server, DAG processor, and metadata database.

## Decision

Run the local Airflow environment using Docker Compose.

Docker provides isolated execution environments, while Docker Compose
coordinates the Airflow services, networking, volumes, and metadata database.

Shared project directories are mounted into the Airflow environment so that
pipeline tasks can access the same data and analytical artifacts.

## Alternatives Considered

- Install Airflow directly in the local Python environment
- Use `airflow standalone`
- Deploy Airflow locally on Kubernetes

## Consequences

### Benefits

- Reproducible local Airflow environment
- No Airflow installation required on the host
- Explicit service configuration
- Shared volumes for pipeline artifacts
- Simple startup and teardown

### Trade-offs

- Requires Docker and Docker Compose
- Adds multiple local containers
- The setup is intended for local development, not production deployment