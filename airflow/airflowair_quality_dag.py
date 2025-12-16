from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os

# Добавляем корень проекта в sys.path, чтобы видеть пакет services
# Это необходимо, так как Airflow может запускать DAG из своей папки dags/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from services.etl import main as etl_main
except ImportError:
    # Заглушка для случая, если импорт упадет при проверке в среде без зависимостей
    def etl_main():
        print("ETL Mock Execution")

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'ecosense_etl_daily',
    default_args=default_args,
    description='Daily ETL for Air Quality Aggregator',
    schedule_interval='@daily',
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['ecosense', 'etl'],
) as dag:

    run_etl = PythonOperator(
        task_id='run_etl_pipeline',
        python_callable=etl_main,
    )

    run_etl
