# Architecture

This project implements a small local and reproducible data platform using:

- Docker for environment reproducibility
- dbt for SQL transformations and testing
- DuckDB as embedded analytical database
- Parquet as local input format
- CSV and Markdown as final artifacts

## Layers

- `staging`: raw input normalization
- `public`: cleaned business-facing tables
- `marts`: final KPI aggregation

## Execution

- `make run`: runs the end-to-end pipeline
- `make test`: runs automated checks