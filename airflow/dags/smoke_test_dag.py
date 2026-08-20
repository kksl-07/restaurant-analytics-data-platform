from datetime import datetime

from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator


with DAG(
    dag_id="smoke_test",
    start_date=datetime(2026, 8, 20),
    schedule=None,
    catchup=False,
    tags=["smoke-test"],
) as dag:

    smoke_test = BashOperator(
        task_id="smoke_test",
        bash_command="echo 'Airflow task executed successfully'",
    )