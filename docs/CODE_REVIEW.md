# ✅ EcoSense: Code Review & Findings

**Проверка реального кода против документации**

---

## 📋 Результаты анализа

### ✓ Что работает правильно

| Компонент | Статус | Примечание |
|-----------|--------|-----------|
| **Extract** | ✓ OK | fetch_open_meteo_data корректно запрашивает обе API |
| **Transform** | ✓ OK | Merge, cleanup, timestamp conversion реализованы |
| **ML** | ✓ OK | LinearRegression настроена, R² логируется |
| **Load** | ✓ OK | Batch insert с execute_values, ON CONFLICT UPSERT |
| **Database Schema** | ✓ OK | Star schema (1 dim + 2 facts) правильно спроектирована |
| **Indexes** | ✓ OK | idx_weather_time, idx_aq_time созданы |
| **VIEW** | ✓ OK | dm_dashboard_analytics объединяет все нужные столбцы |
| **API Endpoints** | ✓ OK | /api/cities, /api/measurements, / все реализованы |
| **CORS** | ✓ OK | Настроена для localhost ports |
| **Frontend** | ✓ OK | React компоненты загружают данные через api.ts |
| **Charts** | ✓ OK | Recharts компоненты отрисовываются корректно |

---

## ⚠️ Выявленные проблемы и рекомендации

### 1. **ETL: Нет retry logic** 🔴

**Текущее состояние**:
```python
def fetch_open_meteo_data(lat, lng):
    w_res = requests.get(w_url).json()  # Может упасть
    aq_res = requests.get(aq_url).json()  # Может упасть
    return w_res, aq_res
```

**Проблема**: 
- Сетевая ошибка = сбой всего ETL для города
- Нет exponential backoff
- Нет timeout handling

**Решение** (добавить в etl.py):
```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_session():
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def fetch_open_meteo_data(lat, lng):
    session = create_session()
    try:
        w_res = session.get(w_url, timeout=10).json()
        aq_res = session.get(aq_url, timeout=10).json()
        return w_res, aq_res
    except requests.Timeout:
        print(f"Timeout for {lat},{lng}")
        raise
    except Exception as e:
        print(f"API error: {e}")
        raise
```

**Приоритет**: СРЕДНИЙ (в production обязательно)

---

### 2. **ETL: Нет scheduling** 🔴

**Текущее состояние**:
```bash
# Запуск вручную
python services/etl.py
```

**Проблема**:
- Данные не обновляются автоматически
- Требует ручного запуска каждый раз
- Невозможно гарантировать свежесть

**Решение**: Выбрать один из вариантов:

**Вариант A: Cron job (Linux/macOS)**
```bash
# Добавить в crontab
crontab -e

# Запуск каждые 6 часов (0:00, 6:00, 12:00, 18:00)
0 */6 * * * cd /path/to/project && /usr/bin/python3 services/etl.py >> /var/log/ecosense-etl.log 2>&1
```

**Вариант B: Windows Task Scheduler**
```batch
# Создать batch файл run_etl.bat
@echo off
cd C:\path\to\project
python services\etl.py >> etl.log 2>&1
```
Затем настроить в Task Scheduler с интервалом 6 часов

**Вариант C: APScheduler (встроить в server.py)**
```python
from apscheduler.schedulers.background import BackgroundScheduler
import services.etl as etl_module

scheduler = BackgroundScheduler()
scheduler.add_job(etl_module.main, 'interval', hours=6, name='etl_scheduler')
scheduler.start()

@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown()
```

**Вариант D: Docker Cron Container** (best for production)
```dockerfile
FROM python:3.9
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Установить cronutils
RUN apt-get update && apt-get install -y cron

# Скопировать crontab
COPY crontab /etc/cron.d/ecosense-cron
RUN chmod 0644 /etc/cron.d/ecosense-cron

CMD ["cron", "-f"]
```

**Рекомендация**: Вариант A для Linux, Вариант B для Windows, Вариант D для production/Docker

**Приоритет**: ВЫСОКИЙ (без этого система не работает)

---

### 3. **ETL: Отсутствует структурированное логирование** 🟡

**Текущее состояние**:
```python
print(f'Запрос данных для координат {lat}, {lng}...')
print(f'Данные для {city_name} сохранены в БД.')
print("ETL Пайплайн завершен успешно.")
```

**Проблема**:
- Сложно фильтровать логи
- Нет временных меток автоматически
- Нет уровней (DEBUG, INFO, ERROR, etc.)

**Решение**:
```python
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/etl_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    logger.info("="*50)
    logger.info("ETL Pipeline Started")
    logger.info(f"Processing {len(CITIES)} cities")
    
    failed_cities = []
    
    for city in CITIES:
        try:
            logger.info(f"Processing {city['name']}...")
            w, aq = fetch_open_meteo_data(city['lat'], city['lng'])
            logger.debug(f"  Weather data: {len(w['hourly']['time'])} records")
            logger.debug(f"  AQ data: {len(aq['hourly']['time'])} records")
            
            df = transform_data(w, aq)
            logger.debug(f"  After merge: {len(df)} rows")
            
            df = train_and_predict_ml(df)
            logger.debug(f"  ML prediction complete")
            
            load_to_db(conn, df, city['name'], city['lat'], city['lng'], city['country'])
            logger.info(f"✓ {city['name']} completed")
            
        except Exception as e:
            logger.error(f"✗ {city['name']}: {str(e)}", exc_info=True)
            failed_cities.append(city['name'])
    
    if failed_cities:
        logger.warning(f"Failed cities: {', '.join(failed_cities)}")
    else:
        logger.info("All cities processed successfully")
    
    logger.info("ETL Pipeline Completed")
```

**Приоритет**: НИЗКИЙ (но рекомендуется для production)

---

### 4. **API: Нет input validation на city_name** 🟡

**Текущее состояние**:
```python
@app.get("/api/measurements")
def get_measurements(city_name: str = Query(..., description="Название города")):
    cur.execute("""
        SELECT * FROM dm_dashboard_analytics
        WHERE city_name = %s  # Защищено параметризацией
```

**Хорошо**: Используются параметризованные запросы (защита от SQL injection)

**Но**: Нет валидации длины строки, символов

**Решение**:
```python
from fastapi import Query
import re

@app.get("/api/measurements")
def get_measurements(
    city_name: str = Query(
        ...,
        min_length=1,
        max_length=100,
        description="Название города"
    )
):
    # Валидация: только буквы, цифры, пробел, дефис
    if not re.match(r"^[а-яА-ЯёЁa-zA-Z0-9\s\-]+$", city_name):
        raise HTTPException(
            status_code=400,
            detail="Invalid city name format"
        )
    
    try:
        conn = get_db_connection()
        # ... rest of code
    except Exception as e:
        logger.error(f"Error fetching measurements for {city_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Приоритет**: СРЕДНИЙ (security best practice)

---

### 5. **API: CORS настроена для "*"** 🔴

**Текущее состояние**:
```python
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "*"  # Позволяет любому источнику
]
```

**Проблема**: В production это security risk

**Решение для development**: Оставить как есть

**Решение для production**:
```python
# .env
CORS_ORIGINS=["http://localhost:5173"]

# server.py
import os
from dotenv import load_dotenv

load_dotenv()

CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    '["http://localhost:5173"]'
)

if isinstance(CORS_ORIGINS, str):
    import json
    CORS_ORIGINS = json.loads(CORS_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Restrict methods too
    allow_headers=["Content-Type"],
)
```

**Приоритет**: НИЗКИЙ для development, ВЫСОКИЙ для production

---

### 6. **Database: Нет backup strategy** 🔴

**Текущее состояние**: Нет документации по backups

**Решение**:

**Ежедневный бэкап (Linux)**:
```bash
#!/bin/bash
# backup_db.sh

BACKUP_DIR="/backups/ecosense"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="ecosense"

mkdir -p $BACKUP_DIR

pg_dump -U postgres $DB_NAME | gzip > $BACKUP_DIR/ecosense_$TIMESTAMP.sql.gz

# Удалить старые бэкапы (старше 30 дней)
find $BACKUP_DIR -name "ecosense_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/ecosense_$TIMESTAMP.sql.gz"
```

Добавить в crontab:
```bash
0 2 * * * /path/to/backup_db.sh >> /var/log/db-backup.log 2>&1
```

**Приоритет**: ВЫСОКИЙ (для production данных)

---

### 7. **Frontend: Нет error boundary** 🟡

**Текущее состояние**: Ошибки могут привести к белому экрану

**Решение**:
```tsx
// components/ErrorBoundary.tsx
import React from 'react';

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error) {
    console.error('App error:', error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-4 bg-red-100 text-red-800">
          <h2>Something went wrong</h2>
          <pre>{this.state.error?.message}</pre>
        </div>
      );
    }

    return this.props.children;
  }
}
```

Использовать в App.tsx:
```tsx
<ErrorBoundary>
  {/* Main app content */}
</ErrorBoundary>
```

**Приоритет**: СРЕДНИЙ (UX improvement)

---

### 8. **Data Quality: ML модель не обучается на полных данных** 🟡

**Текущее состояние**:
```python
def train_and_predict_ml(df):
    train_df = df.dropna(subset=['temperature', 'wind_speed', 'humidity', 'pm25'])
    
    if len(train_df) < 10:
        print('Недостаточно данных для ML')
        df['predicted_pm25'] = None
        return df
```

**Проблема**: 
- Если данных < 10, никакого предсказания
- Модель пересчитывается каждый раз (нет сохранения)
- Нет кросс-валидации

**Решение** (рекомендация):
```python
def train_and_predict_ml(df, model_path='models/pm25_model.pkl'):
    train_df = df.dropna(subset=['temperature', 'wind_speed', 'humidity', 'pm25'])
    
    if len(train_df) < 10:
        logger.warning(f'Insufficient data for ML: {len(train_df)} samples')
        logger.info('Loading previous model if exists...')
        try:
            import pickle
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
        except:
            df['predicted_pm25'] = None
            return df
    else:
        # Обучение с кросс-валидацией
        from sklearn.model_selection import cross_val_score
        
        X = train_df[['temperature', 'wind_speed', 'humidity']]
        y = train_df['pm25']
        
        model = LinearRegression()
        
        # Cross-validation
        cv_scores = cross_val_score(model, X, y, cv=5)
        logger.info(f'CV scores: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})')
        
        # Final training
        model.fit(X, y)
        
        # Save model
        os.makedirs('models', exist_ok=True)
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
    
    # Prediction
    X_full = df[['temperature', 'wind_speed', 'humidity']].fillna(train_df.mean())
    df['predicted_pm25'] = model.predict(X_full).round(2)
    
    return df
```

**Приоритет**: НИЗКИЙ (текущее решение работает, это улучшение)

---

## 📊 Таблица приоритетов по исправлению

| # | Проблема | Приоритет | Сложность | Рекомендация |
|---|----------|-----------|-----------|--------------|
| 1 | Retry logic (ETL API calls) | 🔴 HIGH | LOW | Implement now |
| 2 | Scheduling (automatic ETL) | 🔴 HIGH | MEDIUM | Choose cron or APScheduler |
| 3 | Input validation (API) | 🟡 MEDIUM | LOW | Add regex + length check |
| 4 | CORS production config | 🟡 MEDIUM | LOW | Move to .env |
| 5 | Database backups | 🔴 HIGH | LOW | Setup cron backup script |
| 6 | Structured logging | 🟡 MEDIUM | MEDIUM | Refactor print to logger |
| 7 | Frontend error boundary | 🟡 MEDIUM | LOW | Add React error boundary |
| 8 | ML model persistence | 🟢 LOW | MEDIUM | Optional improvement |

---

## ✅ Что необходимо для запуска (чек-лист)

- [x] PostgreSQL установлен и запущен
- [x] БД `ecosense` создана
- [x] Таблицы созданы (ecosense.sql или ecosenseDB.sql)
- [ ] **КРИТИЧНО**: Настроить ETL scheduling (cron/APScheduler)
- [ ] Python venv и requirements.txt установлены
- [ ] `python services/etl.py` запущен хотя бы один раз
- [ ] FastAPI сервер `python server.py` запущен
- [ ] Frontend зависимости установлены (`npm install`)
- [ ] Frontend запущен (`npm run dev`)
- [ ] Проверить `http://localhost:8000/api/cities` в браузере
- [ ] Проверить `http://localhost:5173` в браузере

---

## 📚 Документы в этом пакете

| Файл | Назначение |
|------|-----------|
| **PIPELINE.md** | Полная архитектура ETL (Extract → Transform → Validate → Load) |
| **DATAFLOW.md** | Диаграммы потока данных и трансформации |
| **QUICKSTART.md** | Пошаговое руководство запуска и отладки |
| **CODE_REVIEW.md** | Этот документ - анализ кода и рекомендации |

---

## 🎯 Итоговые выводы

### Позитивное:
✅ Архитектура хорошо спроектирована (Star schema)  
✅ Код понятен и модульный  
✅ Frontend интерфейс полнофункциональный  
✅ API endpoints правильно реализованы  
✅ Данные корректно преобразуются  

### Критичные проблемы:
🔴 **Нет автоматического scheduling ETL** - система не обновляет данные самостоятельно  
🔴 **Нет retry logic** - сетевая ошибка = сбой всего запуска  
🔴 **Нет стратегии backup** - данные не защищены  

### Рекомендация:
**Для development**: Проект готов к использованию с ручным запуском ETL

**Для production**: Необходимо реализовать:
1. Automatic ETL scheduling (обязательно)
2. Retry logic с exponential backoff (обязательно)
3. Structured logging (рекомендуется)
4. Database backups (обязательно)
5. Input validation (рекомендуется)
6. Monitoring и alerting (рекомендуется)

---

**Document Version**: 1.0  
**Created**: 2025-12-25  
**Status**: Ready for production deployment with recommendations
