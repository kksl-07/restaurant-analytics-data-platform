# Architecture Decision Records

This directory contains the Architecture Decision Records (ADRs) for the
Restaurant Analytics Data Platform.

ADRs document significant architectural decisions made during the evolution
of the platform, including the context, alternatives considered, the chosen
approach, and its consequences.

The goal is to preserve the reasoning behind important technical decisions,
not just the final implementation.

## ADR Structure

Each ADR contains:

- **Context** — the problem or architectural question being addressed
- **Decision** — the chosen approach and why it was selected
- **Alternatives Considered** — other viable approaches that were evaluated
- **Consequences** — benefits and trade-offs introduced by the decision

New ADRs should be created from [`_template.md`](./_template.md).

## Status

An ADR can have one of the following statuses:

- **Proposed** — the decision is under consideration
- **Accepted** — the decision has been adopted
- **Superseded** — the decision has been replaced by a newer ADR
- **Deprecated** — the decision is no longer recommended or relevant

## Naming Convention

ADRs follow the naming convention:

`NNN-short-decision-title.md`

Examples:

- `001-use-docker-compose-for-local-airflow.md`
- `002-use-localexecutor-for-local-orchestration.md`

ADR numbers are sequential and are never reused.

## Decision History

Accepted ADRs should not be rewritten when an architectural decision changes.

Instead:

1. Create a new ADR describing the new decision.
2. Mark the previous ADR as `Superseded`.
3. Reference the new ADR from the previous one.

This preserves the architectural history of the project.

## ADR Index

| ADR | Decision | Status |
|---|---|---|
| [ADR-001](./001-use-docker-compose-for-local-airflow.md) | Use Docker Compose for local Airflow | Accepted |
| [ADR-002](./002-use-localexecutor-for-local-orchestration.md) | Use LocalExecutor for local orchestration | Accepted |
| [ADR-003](./003-use-custom-airflow-runtime-image.md) | Use a custom Airflow runtime image | Accepted |
| [ADR-004](./004-use-postgresql-for-airflow-metadata.md) | Use PostgreSQL for Airflow metadata | Accepted |