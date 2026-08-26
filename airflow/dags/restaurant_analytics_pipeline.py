from datetime import datetime

from airflow.providers.standard.operators.bash import BashOperator

from airflow import DAG

PROJECT_DIR = "/opt/restaurant-platform"


with DAG(
    dag_id="restaurant_analytics_pipeline",
    start_date=datetime(2026, 8, 24),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["restaurant-analytics"],
) as dag:
    generate_raw_data = BashOperator(
        task_id="generate_raw_data",
        bash_command="python scripts/generate_input_data.py",
        cwd=PROJECT_DIR,
        retries=0,
        skip_on_exit_code=None,
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command="dbt build",
        cwd=PROJECT_DIR,
        retries=0,
        skip_on_exit_code=None,
    )

    generate_report = BashOperator(
        task_id="generate_report",
        bash_command="python scripts/generate_report.py",
        cwd=PROJECT_DIR,
        retries=0,
        skip_on_exit_code=None,
    )

    generate_raw_data >> dbt_build >> generate_report
