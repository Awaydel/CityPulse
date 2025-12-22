# Быстрая Справка: Где Найти Ключевые Элементы Проекта

Этот документ служит индексом для быстрого поиска информации по основным аспектам проекта EcoSense Analytics.

---

## Планирование Спринтов

| Что искать | Где найти | Статус |
|------------|-----------|--------|
| **История спринтов** | [`docs/SPRINT_PLANNING.md`](SPRINT_PLANNING.md#спринт-1-инфраструктура-и-архитектура) | 4 из 4 завершены |
| **Текущий статус** | [`docs/SPRINT_PLANNING.md`](SPRINT_PLANNING.md#спринт-4-автоматизация-и-документация) | Спринт 4 Завершён |
| **Бэклог задач** | [`docs/SPRINT_PLANNING.md`](SPRINT_PLANNING.md#бэклог-backlog) | 12 задач в очереди |
| **Метрики velocity** | [`docs/SPRINT_PLANNING.md`](SPRINT_PLANNING.md#метрики-спринтов) | Средняя: 40 SP/sprint |
| **Процесс планирования** | [`docs/SPRINT_PLANNING.md`](SPRINT_PLANNING.md#процесс-sprint-planning) | Описан полностью |
| **Ответственный** | [`docs/PROJECT_MANAGEMENT.md`](PROJECT_MANAGEMENT.md#2-команда-и-роли) | Сидорова Александра (PM) |

---

## Управление Рисками

| Что искать | Где найти | Детали |
|------------|-----------|--------|
| **Реестр рисков** | [`docs/RISK_MANAGEMENT.md`](RISK_MANAGEMENT.md) | 6 рисков идентифицировано |
| **План реагирования** | [`docs/RISK_MANAGEMENT.md`](RISK_MANAGEMENT.md#4-план-мероприятий-по-снижению-рисков-mitigation-plan) | Детальные сценарии |
| **Архитектурные риски** | [`docs/QA_REPORT.md`](QA_REPORT.md#анализ-кодовой-базы) | R-2, R-3, R-4 решены |
| **Визуализация рисков** | [`components/DashboardCharts.tsx`](../components/DashboardCharts.tsx#L167-L218) | Компонент `RiskHeatmap` |
| **Карта рисков в UI** | `App.tsx` → Страница "Дашборд" → Heatmap | Тепловая карта PM2.5 |
| **Red Flags (Красные флаги)** | [`docs/TESTING_PLAN.md`](TESTING_PLAN.md#мониторинг-качества) | 4 критических индикатора |

---

## Отчётность (Техническая)

### A. Отчёты по качеству данных (DQ)

| Тип отчёта | Расположение | Периодичность |
|------------|--------------|---------------|
| **DQ Violations (Нарушения)** | `dq_violations.csv` | Ежедневно (авто) |
| **DQ Report (Полный отчёт)** | `dq_report.csv` | Ежедневно (авто) |
| **DQ Score** | Генерируется в `data_quality.py` | По запросу |
| **Красный флаг** | Логи ETL (если violation > 0.5%) | При превышении |

### B. Отчёты по тестированию

| Тип отчёта | Расположение | Детали |
|------------|--------------|--------|
| **Coverage Report** | `htmlcov/index.html` | 92% покрытие |
| **План тестирования** | [`docs/TESTING_PLAN.md`](TESTING_PLAN.md) | Unit + Integration + E2E |
| **QA Отчёт** | [`docs/QA_REPORT.md`](QA_REPORT.md) | Найденные проблемы + решения |

---

## Разработка DQ-правил

| Элемент | Расположение | Описание |
|---------|--------------|----------|
| **Основной модуль** | [`services/data_quality.py`](../services/data_quality.py) | 195 строк кода |
| **Класс** | `DataQualityChecker` | 5 методов проверки |
| **DQ-1: Schema** | `check_schema()` | Проверка обязательных колонок |
| **DQ-2: Null Values** | `check_null_values()` | NULL в критичных полях |
| **DQ-3: Ranges** | `check_ranges()` | Валидация диапазонов |
| **DQ-4: Uniqueness** | `check_uniqueness()` | Проверка дубликатов |
| **DQ-5: Freshness** | `check_freshness()` | Свежесть данных (<24ч) |
| **Интеграция в ETL** | [`services/etl.py`](../services/etl.py#L76-L90) | Строки 76-90 |
| **Функция валидации** | `validate_air_quality_data()` | Строки 154-194 |
| **Документация** | [`docs/TESTING_PLAN.md`](TESTING_PLAN.md#4-data-quality-качество-данных) | Раздел 4 |
| **Ответственный** | [`docs/PROJECT_MANAGEMENT.md`](PROJECT_MANAGEMENT.md) | QA Team |

### Пример использования DQ-правил

```python
from services.data_quality import validate_air_quality_data
import pandas as pd

# Загрузка данных
df = pd.read_csv('data.csv')

# Валидация
result = validate_air_quality_data(df)

# Результат
print(f"Passed: {result['passed']}")
print(f"Quality Score: {result['quality_score']}")
print(f"Violations: {result['violations_count']}")
```

---

## Реализация Визуализаций в BI-инструменте

### Frontend Компоненты (React)

| Компонент | Файл | Строки | Описание |
|-----------|------|--------|----------|
| **Главный дашборд** | [`App.tsx`](../App.tsx) | 447 | UI layout, навигация, state management |
| **График трендов** | [`DashboardCharts.tsx`](../components/DashboardCharts.tsx#L10-L101) | 10-101 | `TrendsChart` - PM2.5 + ML прогноз |
| **Scatter корреляций** | [`DashboardCharts.tsx`](../components/DashboardCharts.tsx#L105-L165) | 105-165 | `CorrelationChart` - PM2.5 vs метео |
| **Тепловая карта** | [`DashboardCharts.tsx`](../components/DashboardCharts.tsx#L169-L218) | 169-218 | `RiskHeatmap` - карта рисков |

### Структура Дашборда

| Страница | Компонент | Ключевые виджеты |
|----------|-----------|------------------|
| **Страница 1: Мониторинг** | `App.tsx` (activeView='dashboard') | Health Widget, Тренды, Heatmap, Корреляции |
| **Страница 2: Данные** | `App.tsx` (activeView='data') | Таблица raw данных из БД |
| **Страница 3: Логи ETL** | `App.tsx` (activeView='logs') | Журнал операций, команды запуска |

### Спецификация

| Документ | Расположение | Содержание |
|----------|--------------|------------|
| **Техническое задание** | [`docs/DASHBOARD_SPECS.md`](DASHBOARD_SPECS.md) | 3 страницы, требования к каждой |
| **Оветственный** | [`docs/PROJECT_MANAGEMENT.md`](PROJECT_MANAGEMENT.md) | Frontend Developers |

---

## Контакты и Помощь

| Вопрос по теме | Кому обратиться |
|----------------|-----------------|
| Планирование, риски, процессы | Сидорова Александра (PM) |
| Архитектура, API, Airflow | Серебряков Айрат, Зубков Максим |
| ETL, БД, ML модель | Титков Андрей |
| Тестирование, DQ-правила, аналитика | Бурнаев Андрей, Красов Константин |
| Дашборд, визуализации | QA & Аналитики Team |

---

**Версия:** 1.1
**Дата обновления:** 17.12.2025
**Составил:** Project Management Team
