# 🔧 EcoSense: Практическое руководство по запуску и отладке

---

## ⚡ Быстрый старт (5 минут)

### 1. Инициализация БД

```bash
# Windows (PowerShell)
psql -U postgres -d ecosense -f ecosenseDB.sql

# Linux/macOS
psql -U postgres -d ecosense -f ecosenseDB.sql
```

### 2. Backend

```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать (Windows)
venv\Scripts\activate
# Активировать (Linux/macOS)
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Запустить ETL (заполнить БД данными)
python services/etl.py

# Запустить сервер
python server.py
```

**Ожидаемый результат**:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3. Frontend

```bash
# Новый терминал
npm install
npm run dev
```

**Ожидаемый результат**:
```
VITE v6.2.0  ready in 1234 ms

➜  Local:   http://localhost:5173/
```

---

## 🔍 Проверка каждого компонента

### API Health Check

```bash
# Проверить, запущен ли сервер
curl http://localhost:8000/

# Результат:
# {"status":"EcoSense API is running"}
```

### Список городов

```bash
curl http://localhost:8000/api/cities | jq .

# Результат:
# {
#   "cities": [
#     {
#       "city_id": 1,
#       "name": "Москва",
#       "country_code": "RU",
#       "latitude": 55.7558,
#       "longitude": 37.6173
#     },
#     ...
#   ]
# }
```

### Данные по городу

```bash
# Windows (PowerShell)
$city = "Москва"
Invoke-WebRequest -Uri "http://localhost:8000/api/measurements?city_name=$city" | ConvertFrom-Json | ConvertTo-Json -Depth 5

# Linux/macOS (curl)
curl "http://localhost:8000/api/measurements?city_name=Москва" | jq .
```

### Swagger UI (интерактивная документация)

Откройте в браузере: **http://localhost:8000/docs**

---

## 📊 ETL Pipeline: Пошаговая отладка

### Проверка подключения к БД

```python
# В Python интерпретаторе
import psycopg2

DB_CONFIG = {
    'dbname': 'ecosense',
    'user': 'postgres',
    'password': '123',
    'host': '127.0.0.1',
    'port': 5432
}

try:
    conn = psycopg2.connect(**DB_CONFIG)
    print("✓ Подключение успешно")
    
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM dim_city")
    count = cur.fetchone()[0]
    print(f"✓ Городов в БД: {count}")
    
    conn.close()
except Exception as e:
    print(f"✗ Ошибка: {e}")
```

### Проверка API Open-Meteo

```python
import requests

lat, lng = 55.7558, 37.6173  # Москва

# Погода
w_url = f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&past_days=7&forecast_days=1&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m'
w_res = requests.get(w_url).json()

print(f"✓ Погода: {len(w_res['hourly']['time'])} записей")
print(f"  Первая запись: {w_res['hourly']['time'][0]}")
print(f"  Температура: {w_res['hourly']['temperature_2m'][0]}°C")

# Воздух
aq_url = f'https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lng}&past_days=7&forecast_days=1&hourly=pm10,pm2_5'
aq_res = requests.get(aq_url).json()

print(f"✓ Воздух: {len(aq_res['hourly']['time'])} записей")
print(f"  PM2.5: {aq_res['hourly']['pm2_5'][0]} µg/m³")
```

### Запуск ETL с логированием

```bash
# Вариант 1: С вывод в консоль
python services/etl.py

# Вариант 2: С логами в файл
python services/etl.py > etl.log 2>&1

# Вариант 3: Отладочный режим (добавить в etl.py)
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Проверка данных в БД после ETL

```python
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {...}
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor(cursor_factory=RealDictCursor)

# 1. Города
cur.execute("SELECT * FROM dim_city")
cities = cur.fetchall()
print(f"✓ Городов: {len(cities)}")

# 2. Последняя дата в погоде
cur.execute("SELECT MAX(timestamp) as max_time FROM fact_weather")
max_time = cur.fetchone()['max_time']
print(f"✓ Последние данные о погоде: {max_time}")

# 3. Качество воздуха
cur.execute("SELECT COUNT(*) as cnt FROM fact_air_quality WHERE pm25 IS NOT NULL")
pm_count = cur.fetchone()['cnt']
print(f"✓ Записей с PM2.5: {pm_count}")

# 4. Одна запись из view
cur.execute("SELECT * FROM dm_dashboard_analytics LIMIT 1")
sample = cur.fetchone()
print(f"✓ Пример данных: {sample}")

cur.close()
conn.close()
```

---

## 🐛 Типовые ошибки и решения

### Ошибка: "psycopg2.OperationalError: could not connect to server"

**Причина**: PostgreSQL не запущен или неверные учетные данные

**Решение**:
```bash
# Windows: Проверить сервис в Services.msc
# macOS: brew services start postgresql
# Linux: sudo systemctl start postgresql

# Проверить соединение
psql -U postgres -h 127.0.0.1 -d ecosense -c "SELECT 1"
```

### Ошибка: "relation \"dim_city\" does not exist"

**Причина**: Таблицы не созданы

**Решение**:
```bash
psql -U postgres -d ecosense -f ecosense.sql
# или
psql -U postgres -d ecosense -f ecosenseDB.sql
```

### Ошибка: "Данные не найдены. Запустите etl.py"

**Причина**: БД пуста, ETL еще не запущен

**Решение**:
```bash
python services/etl.py
# Подождать 30-60 секунд, затем обновить страницу
```

### Ошибка: "CORS error" в браузере

**Причина**: Backend и Frontend на разных портах

**Решение**: 
- Backend слушает на `http://0.0.0.0:8000` ✓
- Frontend на `http://localhost:5173` ✓
- CORS настроен в `server.py` ✓

Если ошибка остается, добавить в `server.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production: ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Ошибка: "Failed to fetch /api/measurements"

**Диагностика**:
```bash
# 1. Проверить API напрямую
curl "http://localhost:8000/api/measurements?city_name=Москва"

# 2. Проверить логи сервера
# (обратить внимание на 500 ошибки, timeout и т.д.)

# 3. Проверить консоль браузера (F12)
# (CORS, network error, неверный URL)
```

---

## 📈 Мониторинг системы

### Dashboard метрики

**В интерфейсе отображаются**:
- Current PM2.5 (последнее значение)
- Days Exceeding WHO (дни с PM2.5 > 15)
- Quality Score (% полноты данных)
- Missing data (кол-во пропусков)
- Timestamp issues (нарушения порядка)
- Anomalies (скачки > 50%)

### Проверка свежести данных

```python
import psycopg2
from datetime import datetime, timezone

conn = psycopg2.connect(...)
cur = conn.cursor()

cur.execute("""
    SELECT 
        (NOW() AT TIME ZONE 'UTC') - MAX(timestamp) as data_age
    FROM dm_dashboard_analytics
""")

age = cur.fetchone()[0]
print(f"Возраст данных: {age}")

if age.total_seconds() / 3600 > 6:
    print("⚠️ Данные старые, ETL возможно не запускался 6+ часов")
```

### Производительность запросов

```python
import psycopg2
import time

conn = psycopg2.connect(...)

# Тест на скорость
start = time.time()
cur = conn.cursor()
cur.execute("SELECT * FROM dm_dashboard_analytics WHERE city_name = %s LIMIT 168", ("Москва",))
data = cur.fetchall()
elapsed = time.time() - start

print(f"✓ Получено {len(data)} строк за {elapsed*1000:.2f}ms")
```

---

## 🔄 Re-запуск ETL

### Полная переиндексация (очистка + новые данные)

```bash
# 1. Очистить факт-таблицы (но не справочник)
psql -U postgres -d ecosense -c "
    TRUNCATE TABLE fact_weather;
    TRUNCATE TABLE fact_air_quality;
"

# 2. Запустить ETL заново
python services/etl.py

# 3. Проверить результаты
psql -U postgres -d ecosense -c "SELECT COUNT(*) FROM fact_weather"
```

### Частичное обновление (для одного города)

Отредактировать `services/etl.py`:
```python
# В main():
CITIES_TO_PROCESS = [
    {'name': 'Москва', 'lat': 55.7558, 'lng': 37.6173, 'country': 'RU'},
]

# Вместо:
for city in CITIES:
```

Запустить:
```bash
python services/etl.py
```

---

## 📝 Логирование

### Где находятся логи

| Компонент | Логи | Место |
|-----------|------|-------|
| Frontend (React) | Browser console | F12 → Console |
| Backend (FastAPI) | Server output | Terminal / stdout |
| ETL (Python) | Print statements | Terminal / stdout |
| Database | PostgreSQL logs | `/var/log/postgresql/` (Linux) |

### Увеличить логирование (для отладки)

**В `server.py`**:
```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.debug(f"Query parameters: {city_name}")
```

**В `services/etl.py`**:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Использование
logger.info(f"Processing {city['name']}...")
logger.error(f"Failed: {e}")
```

---

## 🚀 Optimization Tips

### Ускорить ETL

```python
# Текущее: последовательная обработка городов
# for city in CITIES:
#     fetch_open_meteo_data(...)  # 5s per city
# Total: 65 seconds

# Оптимизация: асинхронная загрузка
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def process_cities():
    with ThreadPoolExecutor(max_workers=4) as executor:
        tasks = [
            asyncio.to_thread(process_city, city)
            for city in CITIES
        ]
        await asyncio.gather(*tasks)

# Total: ~20 seconds
```

### Кэширование API

```python
from functools import lru_cache
from datetime import datetime, timedelta

# Кэшировать на 1 час
@lru_cache(maxsize=128)
def fetch_cached(lat, lng, date):
    return fetch_open_meteo_data(lat, lng)

# Использование
cache_key = (lat, lng, datetime.now().date().isoformat())
return fetch_cached(lat, lng, cache_key)
```

### Индексирование БД

Индексы уже есть:
```sql
CREATE INDEX idx_weather_time ON fact_weather(timestamp);
CREATE INDEX idx_aq_time ON fact_air_quality(timestamp);
```

Добавить если нужна фильтрация по городу:
```sql
CREATE INDEX idx_weather_city_time ON fact_weather(city_id, timestamp);
CREATE INDEX idx_aq_city_time ON fact_air_quality(city_id, timestamp);
```

---

## 📦 Переменные окружения (рекомендация)

Создать `.env`:
```
DB_NAME=ecosense
DB_USER=postgres
DB_PASSWORD=123
DB_HOST=127.0.0.1
DB_PORT=5432

API_HOST=0.0.0.0
API_PORT=8000

FRONTEND_URL=http://localhost:5173

LOG_LEVEL=INFO
```

Использовать в коде:
```python
from dotenv import load_dotenv
import os

load_dotenv()

DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT')),
}
```

---

## 🔐 Security Checklist

- [ ] Пароль БД НЕ в коде (использовать .env)
- [ ] CORS ограничить: `["http://localhost:5173"]` вместо `["*"]`
- [ ] SQL injection: Используются параметризованные запросы ✓
- [ ] Rate limiting: Добавить на API endpoints
- [ ] Input validation: Проверить city_name параметр
- [ ] HTTPS: Включить в production

**Пример валидации**:
```python
from fastapi import Query
import re

@app.get("/api/measurements")
def get_measurements(city_name: str = Query(..., min_length=1, max_length=100)):
    # city_name содержит только буквы/цифры/пробел
    if not re.match(r"^[а-яА-ЯёЁa-zA-Z0-9\s\-]+$", city_name):
        raise HTTPException(status_code=400, detail="Invalid city name")
    # ...
```

---

## 📞 Полезные команды

```bash
# PostgreSQL
psql -U postgres                          # Connect as postgres
psql -U postgres -d ecosense              # Connect to ecosense DB
psql -U postgres -d ecosense -f file.sql  # Execute SQL file
\dt                                       # List tables
\dv                                       # List views
SELECT COUNT(*) FROM table_name;          # Count rows

# Python
python services/etl.py                    # Run ETL
python -m pip list                        # List installed packages
python -c "import psycopg2; print('OK')"  # Check import

# Node.js
npm install                               # Install dependencies
npm run dev                               # Dev server
npm run build                             # Build production
npm run preview                           # Preview build

# Network
curl http://localhost:8000/               # Test API
netstat -tlnp | grep 8000                 # Check port (Linux)
netstat -ano | findstr :8000              # Check port (Windows)
```

---

**Last Updated**: 2025-12-25
