# План тестирования EcoSense (Air Quality Aggregator)

## Обзор

Документ описывает комплексную стратегию тестирования проекта EcoSense, включая пирамиду тестов, виды проверок и критерии приемки.

---

## Цели тестирования

1. **Unit-тесты**: Покрытие ключевой логики ≥ 70%
2. **Интеграционные тесты**: Проверка работы с БД и внешними системами
3. **End-to-End (E2E)**: Сквозной сценарий от ETL до API
4. **Data Quality**: Проверка качества данных (схемы, диапазоны, свежесть)

---

## Пирамида тестов

```
           /\
          /E2E\          1 сквозной сценарий
         /------\
        /  Integ.\       Тесты с реальной БД
       /----------\
      / Unit Tests \     70%+ покрытие логики
     /--------------\
```

### 1. **Unit-тесты (База пирамиды)**

**Покрытие**: ≥ 70% для `services/etl.py` и `server.py`

**Файлы**:
- `tests/test_etl.py` - тестирование ETL логики
- `tests/test_api.py` - тестирование API эндпоинтов

**Тестируемые функции**:
- `fetch_open_meteo_data()` - получение данных от внешнего API
- `transform_data()` - трансформация и очистка данных
- `train_and_predict_ml()` - обучение ML модели
- `get_db_connection()` - подключение к БД (mocked)
- `load_to_db()` - загрузка в БД (mocked)
- `main()` - основной процесс
- API эндпоинты (`/api/cities`, `/api/measurements`)

**Запуск**:
```bash
pytest tests/test_etl.py tests/test_api.py --cov=services --cov=server
```

**Текущее покрытие**: 92% (превышает цель 70%)

---

### 2. **Интеграционные тесты**

**Цель**: Проверка взаимодействия с реальной PostgreSQL БД

**Файл**: `tests/test_integration.py`

**Сценарии**:
- Round-trip тест: запись → чтение → сравнение
- UPSERT проверка (ON CONFLICT)
- Проверка связанных таблиц (`dim_city`, `fact_weather`, `fact_air_quality`)

**Требования**: 
- Запущенная PostgreSQL с БД `ecosense`
- Настроенные таблицы согласно `ecosense.sql`

**Запуск**:
```bash
pytest tests/test_integration.py -v
```

---

### 3. **End-to-End (E2E) тесты**

**Цель**: Проверка полного пайплайна от ETL до API

**Файл**: `tests/test_e2e.py`

**Сценарий**:
1. Подготовка mock-данных (имитация Open-Meteo API)
2. Запуск `transform_data()` → `train_and_predict_ml()` → `load_to_db()`
3. Вызов API `/api/measurements`
4. Проверка корректности данных в ответе API

**Запуск**:
```bash
pytest tests/test_e2e.py -v
```

---

### 4. **Data Quality (Качество данных)**

**Модуль**: `services/data_quality.py`

**Класс**: `DataQualityChecker`

**Проверки**:

| Проверка | Описание | Severity |
|----------|----------|----------|
| **Schema** | Наличие обязательных колонок | CRITICAL |
| **Null Values** | NULL в критичных полях | WARNING |
| **Ranges** | Диапазоны значений (температура, PM2.5, влажность) | ERROR |
| **Uniqueness** | Дубликаты по ключевым полям | ERROR |
| **Freshness** | Свежесть данных (не старее 24ч) | WARNING |

**Правила диапазонов**:
- `temperature`: [-50, 60] °C
- `humidity`: [0, 100] %
- `wind_speed`: [0, 200] km/h
- `pm10`: [0, 500] μg/m³
- `pm25`: [0, 300] μg/m³

**Функции**:
- `validate_air_quality_data(df)` - комплексная валидация
- `generate_report()` - генерация CSV отчета о нарушениях
- `get_quality_score()` - оценка качества (0-100)

**Тесты**: `tests/test_data_quality.py`

**Запуск**:
```bash
pytest tests/test_data_quality.py -v
```

**Интеграция в ETL**: 
Модуль уже встроен в `services/etl.py` для автоматической проверки на этапе трансформации.

---

## Автоматический запуск

### Скрипт: `scripts/run_tests.py`

Запускает все категории тестов с отчетами:

```bash
python scripts/run_tests.py
```

**Что выполняется**:
1. Unit-тесты (ETL + API) с coverage
2. Data Quality тесты
3. Интеграционные тесты
4. E2E тесты
5. Общий coverage report (HTML)

**Выходные файлы**:
- `htmlcov/index.html` - HTML отчет о покрытии кода
- `dq_violations.csv` - нарушения качества данных (если есть)
- `dq_report.csv` - полный отчет DQ

---

## Критерии приемки

✅ **Выполнено**:
- [x] Unit-тесты: покрытие ≥ 70% (текущее: 92%)
- [x] Интеграционные тесты с реальной БД
- [x] E2E тест (сквозной сценарий ETL → API)
- [x] Модуль Data Quality с автоматическими проверками
- [x] Скрипт автозапуска тестов
- [x] Отчеты о покрытии и качестве данных

---

## Настройка окружения

### Установка зависимостей:
```bash
pip install -r requirements.txt
```

### Настройка БД для тестов:
```bash
# Создать БД ecosense
psql -U postgres -c "CREATE DATABASE ecosense;"

# Применить схему
psql -U postgres -d ecosense -f ecosense.sql
```

### Конфигурация pytest:
Файл `pytest.ini` уже настроен с параметрами:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
```

---

---

## Мониторинг качества

### Red Flags (Красные флаги):

1. **Покрытие < 70%** - недостаточное тестирование
2. **Quality Score < 70** - критические проблемы с данными
3. **Violation Rate > 0.5%** - превышение порога аномалий
4. **ML Model R² < 0.3** - низкая точность предсказаний
