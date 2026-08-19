#!/usr/bin/env bash

set -euo pipefail

APP_DIR="/app"

echo "==> Starting restaurant analytics pipeline"

cd "${APP_DIR}"

echo "==> Running dbt build"
dbt build

echo "==> Generating report"
python "${APP_DIR}/scripts/generate_report.py"

echo "==> Pipeline completed successfully"
echo
echo "Outputs:"
echo " - ${HOST_PATH}/exports/cleaned/"
echo " - ${HOST_PATH}/exports/marts/restaurant_kpis.csv"
echo " - ${HOST_PATH}/exports/reports/summary_report.md"