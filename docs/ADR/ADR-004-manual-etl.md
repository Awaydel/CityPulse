# ADR-004: Ручной запуск ETL вместо Airflow



⚠️ Временное решение

## Контекст

ТЗ требует оркестрацию через Airflow с автоматическим запуском по расписанию.

## Решение

На текущем этапе ETL запускается **вручную** через `python services/etl.py`.

## Обоснование

| Критерий | Airflow | Ручной запуск |
|----------|---------|---------------|
| Сложность настройки | Высокая (Docker, DB, Webserver) | Низкая |
| Время разработки | +1-2 дня | 0 |
| Автоматизация | Полная | Отсутствует |
| Мониторинг | Встроенный UI | Логи в консоли |

## Последствия

### Положительные
- Быстрый старт проекта
- Меньше инфраструктуры

### Отрицательные
- Нет автоматического обновления данных
- Нет централизованного мониторинга
- Не соответствует ТЗ полностью

## План миграции на Airflow

1. Установить Airflow (Docker Compose)
2. Создать DAG `ecosense_etl_dag.py`
3. Настроить расписание (ежедневно/ежечасно)
4. Добавить алерты на ошибки

```python
# dags/ecosense_etl_dag.py (пример)
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'ecosense',
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'ecosense_etl',
    default_args=default_args,
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:
    
    run_etl = PythonOperator(
        task_id='run_etl_pipeline',
        python_callable=main,  # from services.etl import main
    )
```
