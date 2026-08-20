#!/usr/bin/env bash

set -euo pipefail

APP_DIR="/app"

echo "==> Running dbt build"

cd "${APP_DIR}"

dbt build

echo "==> Data quality checks completed successfully"