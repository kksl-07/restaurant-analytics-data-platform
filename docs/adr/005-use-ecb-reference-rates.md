# ADR-005: Use ECB Reference Rates for Local FX Ingestion

**Status:** Accepted  
**Date:** 2026-11-19

## Context

The platform previously contained only fixed EUR/GBP conversion factors in the
restaurant KPI mart. Issue #12 introduces a source-level ingestion capability
for historical ECB reference rates without changing existing dbt models, KPI
definitions, reporting contracts, or Airflow orchestration.

The ingestion must retain daily historical observations, support revisions,
operate locally, and preserve a valid dataset if a network, validation, or
persistence failure occurs.

## Decision

Use the official ECB SDMX Data API series `EXR/D.GBP.EUR.SP00.A`, which reports
GBP per EUR, as the initial source. Persist a local generated Parquet snapshot
at `data/raw/ecb_fx_rates.parquet` with grain and business key
`(rate_date, quote_currency)`. Store rates as `DECIMAL(20,10)` through an
explicit Arrow schema.

The first ingestion backfills from 2024-01-01. Incremental runs re-fetch an
inclusive seven-calendar-day overlap ending at the latest persisted date so ECB
revisions replace matching keys. Explicit start/end dates provide historical
replay. The process validates source and existing data, merges idempotently,
and atomically replaces the local Parquet file only after validation succeeds.

## Alternatives Considered

- Keep fixed FX factors only: preserves deterministic calculations but cannot
  retain historical ECB observations or revisions.
- Use a commercial FX provider: may provide broader coverage or settlement
  rates, but adds credentials, cost, and unnecessary infrastructure.
- Store the data in DuckDB: couples source ingestion to the analytical store
  and complicates source-level reuse.
- Use a separate watermark database: adds state infrastructure when the latest
  valid Parquet observation supplies the needed incremental boundary.
- Full reload on every run: is simpler but re-downloads unnecessary history and
  does not explicitly target recent revisions.

## Consequences

### Benefits

- Official, public reference-rate provenance with no credentials.
- Local Parquet remains portable and queryable by future dbt work.
- Seven-day overlap plus replay supports correction of recent and older data.
- Validation and atomic replacement preserve the last valid local snapshot.
- Offline unit tests keep CI deterministic and independent of ECB availability.

### Trade-offs

- ECB reference rates are benchmark daily observations, not payment execution
  or settlement rates.
- The ingestion command requires external network availability; it is kept out
  of the core `make run`, `make test`, CI, and Airflow paths.
- Revisions older than seven days require an explicit replay.
- The implementation assumes one local writer and intentionally does not add
  locking or distributed state.
