# Repository Guidance

## Scope and architecture

This is a self-contained, local analytics platform: deterministic synthetic
Parquet sources flow through DuckDB and dbt, then into a Python reporting
consumer. Apache Airflow orchestrates the same workflow; it does not contain
transformation or KPI business logic.

Keep these boundaries intact:

- dbt owns analytical KPI definitions; Python consumes validated dbt models
  and validates its consumer contract.
- `dbt build` is the quality gate before reporting. A dbt failure must prevent
  report generation.
- Preserve `mart_restaurant_kpis` at one row per active restaurant and preserve
  its consumer contract unless an explicitly reviewed change updates all
  consumers and documentation.
- Do not duplicate business logic across dbt, Python, and Airflow. Do not add
  cloud infrastructure or roadmap capabilities without an approved decision.
- Modify only files relevant to the assigned task; avoid unrelated refactors or
  formatting changes, and report out-of-scope issues separately.

Read `README.md` for operating instructions and `docs/architecture.md` for
architecture detail; do not copy them into new documentation.

## Repository map

- `models/staging/`: source-level normalization; preserve source semantics.
- `models/public/`: validated, business-facing cleaned relations.
- `models/marts/`: analytical aggregation and KPI definitions.
- `models/schema.yml` and `tests/`: dbt schema and business-invariant tests.
- `scripts/`: deterministic data generation, standalone pipeline, and reporting
  consumer.
- `airflow/dags/`: orchestration only.
- `profiles/`: local dbt profile; `data/`, `exports/`, `.duckdb/`, `logs/`, and
  `target/` contain generated or runtime state.
- `docs/adr/`: architecture decision records.

## Python and SQL

- Target Python 3.12. Use clear types where they aid contracts, small focused
  functions, `pathlib` for paths, and explicit error handling at I/O boundaries.
- Ruff is authoritative: line length 88, target `py312`, and lint rules `E`,
  `F`, and `I`. Run `ruff check .` and `ruff format --check .`; use
  `ruff format .` only when intentionally reformatting changed Python files.
- Use lowercase SQL keywords, four-space indentation, descriptive CTE names,
  and `ref()` for dbt model dependencies. Prefer explicit column projections in
  new or modified SQL; do not rewrite an existing query solely to remove
  `select *`.
- State a model's grain and business key before changing its joins or measures.
  Pre-aggregate or use distinct keys where needed to prevent fan-out and
  duplicate counting. Do not sum restaurant-grain distinct-user metrics into a
  platform-wide distinct count.
- Financial metric changes require explicit treatment of currency, payment
  status, rounding, and the reconciliation `gross = platform fee + merchant
  proceeds`. Preserve the deterministic fixed-FX approach unless an approved
  architectural decision changes it.
- Avoid concurrent writers to the same DuckDB file. Account for shared database
  access when validating local and Airflow execution.

## dbt quality requirements

- Keep layering `staging -> public -> marts`; apply technical normalization in
  staging, validation in public, and KPI aggregation in marts.
- Add or update schema tests and custom tests for changed keys, accepted values,
  relationships, financial invariants, and mart grain as appropriate.
- Validate changes with `dbt build --profiles-dir ./profiles` after generating
  required input data. Reporting may run only after this succeeds.

## Airflow

- DAGs must express dependencies explicitly and keep reporting downstream of
  `dbt_build`. Tasks should call existing scripts or dbt commands rather than
  embed analytical SQL or calculations.
- Configure deterministic task IDs, appropriate retry/failure behavior, and no
  silent failure or success masking. Keep DAG imports lightweight and local
  development compatible.

## Local commands

Use the Makefile targets as the source of truth:

```bash
make build          # build the platform image
make generate-data  # build image and write synthetic raw data
make run            # build, ensure data, dbt build, then generate report
make test           # build, ensure data, then dbt build; writes runtime state
make docs-generate  # generate dbt documentation artifacts
make docs-serve     # serve dbt docs on port 8080
make clean          # delete generated outputs/runtime state
make clean-all      # also delete generated raw Parquet inputs
docker compose up -d  # start local Airflow services
```

`make test`, `make run`, generation, docs generation, and cleanup mutate local
data or artifacts; do not treat them as read-only checks. CI runs Python 3.12,
installs both requirements files, runs Ruff lint/format checks, generates data,
then runs `dbt build --profiles-dir ./profiles`.

`make docs-serve` uses port 8080, which may conflict with local Airflow; stop
the conflicting service or use a different port before starting either service.

## Git, tests, and review

- Work on a focused feature branch; never modify `main` directly. Never commit,
  push, create a PR, merge, or perform destructive Git operations without
  explicit approval. Use concise, imperative Conventional Commit-style messages
  (for example, `docs: ...`).
- Keep pull requests narrowly scoped. Explain model grain, contract, KPI, or
  financial impacts; include validation performed and generated artifacts left
  untracked. Request review before merging.
- Before requesting review, inspect `git diff`, run `git diff --check`, run the
  relevant Ruff checks for Python changes, and run the appropriate dbt quality
  gate for model or reporting changes. Never claim a check passed unless it was
  executed; report each exact command, result, and skipped check with its reason.

## Security, artifacts, and documentation

- Never commit credentials, `.env` files, tokens, production data, or local
  databases. Use environment variables for configuration and keep secrets out
  of logs, reports, and examples.
- Do not add generated raw data, DuckDB files, dbt `target/` or `logs/`, or
  generated exports to Git; retain only documented `.gitkeep`/example files.
- Update the closest documentation when behavior, contracts, or operations
  change. For material architectural decisions, add the next numbered ADR using
  `docs/adr/_template.md`, with context, decision, alternatives, and
  consequences; do not rewrite prior ADRs.
