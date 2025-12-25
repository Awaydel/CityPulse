from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os

# Добавляем корневую директорию проекта в sys.path, чтобы видеть services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.etl import extract_all, transform_all, validate_all, load_all

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'air_quality_pipeline',
    default_args=default_args,
    description='ETL pipeline for Air Quality and Weather data',
    schedule_interval='0 * * * *', # Каждый час
    catchup=False
)

t_extract = PythonOperator(
    task_id='extract',
    python_callable=extract_all,
    dag=dag,
)

t_transform = PythonOperator(
    task_id='transform',
    python_callable=transform_all,
    dag=dag,
)

t_validate = PythonOperator(
    task_id='validate',
    python_callable=validate_all,
    dag=dag,
)

t_load = PythonOperator(
    task_id='load',
    python_callable=load_all,
    dag=dag,
)

t_extract >> t_transform >> t_validate >> t_load
