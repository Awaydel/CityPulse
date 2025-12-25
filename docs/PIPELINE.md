# 🔄 EcoSense Analytics: ETL Pipeline Architecture

**Полное описание: как устроено и как работает система мониторинга качества воздуха**

---

## 📑 Содержание

1. [Общая архитектура](#общая-архитектура)
2. [Данные: Источники](#данные-источники)
3. [Extract: Сбор данных](#extract-сбор-данных)
4. [Transform: Преобразование](#transform-преобразование)
5. [Validate (DQ): Контроль качества](#validate-dq-контроль-качества)
6. [Load: Загрузка в БД](#load-загрузка-в-бд)
7. [Storage: Витрина данных](#storage-витрина-данных)
8. [API: REST endpoints](#api-rest-endpoints)
9. [UI: Фронтенд](#ui-фронтенд)
10. [Scheduling & Monitoring](#scheduling--monitoring)
11. [Error Handling & Retry Logic](#error-handling--retry-logic)

---

## 🏗️ Общая архитектура

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES (EXTERNAL)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Open-Meteo Weather API  │  Open-Meteo Air Quality API                      │
│  (температура, влажность,│  (PM2.5, PM10)                                   │
│   скорость ветра)        │                                                   │
└────────┬──────────────────────────────────────────────────────────────────────┘
         │
         │  EXTRACT (Fetch historical + recent data)
         ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ETL PIPELINE (Python)                               │
│                       services/etl.py                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ EXTRACT PHASE                                                       │   │
│  │ • fetch_open_meteo_data(lat, lng)                                   │   │
│  │ • Historical: past_days=7 + forecast_days=1                         │   │
│  │ • Hourly granularity                                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ TRANSFORM PHASE                                                     │   │
│  │ • transform_data(w_data, aq_data)                                   │   │
│  │ • Merge weather + air quality on timestamp                          │   │
│  │ • Remove negative PM values (outliers)                              │   │
│  │ • train_and_predict_ml(df)                                          │   │
│  │ • Linear Regression: predict PM2.5 from (temp, wind, humidity)      │   │
│  │ • Add predicted_pm25 column                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ VALIDATE PHASE (Data Quality Checks)                                │   │
│  │ • Check data completeness (nulls, NaNs)                             │   │
│  │ • Check value ranges (PM >= 0, temp realistic)                      │   │
│  │ • Check timestamp monotonicity                                      │   │
│  │ • Detect anomalies (sudden spikes > 50% change)                     │   │
│  │ • Log validation results                                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ LOAD PHASE                                                          │   │
│  │ • load_to_db(conn, df, city_name, lat, lng, country)               │   │
│  │ • Upsert dim_city (справочник городов)                              │   │
│  │ • Batch insert into fact_weather (execute_values)                   │   │
│  │ • Batch insert into fact_air_quality                                │   │
│  │ • Handle conflicts: ON CONFLICT DO UPDATE                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└────────┬──────────────────────────────────────────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DATABASE LAYER (PostgreSQL)                            │
│                                                                             │
│  Dimension Tables:           Fact Tables:          Aggregates:             │
│  • dim_city                  • fact_weather        • dm_dashboard_analytics │
│    - city_id (PK)              - weather_id (PK)    (SQL VIEW)             │
│    - name                       - city_id (FK)     - Joins facts+dims      │
│    - country_code              - timestamp         - Ready for API         │
│    - latitude                  - temperature                               │
│    - longitude                 - humidity                                  │
│                                - wind_speed       Indexes:                 │
│                              - created_at         • idx_weather_time       │
│                              - UNIQUE(city_id,    • idx_aq_time           │
│                                timestamp)                                  │
│                                                                            │
│                            • fact_air_quality                              │
│                              - aq_id (PK)                                  │
│                              - city_id (FK)                                │
│                              - timestamp                                   │
│                              - pm10                                        │
│                              - pm25                                        │
│                              - predicted_pm25 (ML)                         │
│                              - created_at                                  │
│                              - UNIQUE(city_id,                             │
│                                timestamp)                                  │
└────────┬──────────────────────────────────────────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                    REST API (FastAPI / Python)                              │
│                           server.py                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  GET /api/cities                                                            │
│    → Returns all monitored cities from dim_city                             │
│    → Used: UI city selector                                                │
│                                                                             │
│  GET /api/measurements?city_name={city_name}                                │
│    → Query dm_dashboard_analytics WHERE city_name = ?                       │
│    → Returns: last 168 rows (7 days × 24 hours)                             │
│    → Columns: city_name, timestamp, temperature, humidity, wind_speed,     │
│              pm10, pm25, predicted_pm25                                     │
│    → Used: Dashboard charts                                                │
│                                                                             │
│  GET /                                                                      │
│    → Health check: {"status": "EcoSense API is running"}                    │
│    → Used: API availability test                                           │
│                                                                             │
│  CORS: Enabled for localhost:3000, localhost:5173, *                       │
│  Server: Uvicorn @ http://0.0.0.0:8000                                     │
│  Docs: Swagger @ http://localhost:8000/docs                                │
└────────┬──────────────────────────────────────────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                 CLIENT (TypeScript / React + Vite)                          │
│                         Fронтенд                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  Entry Point:             Core Components:        Data Flow:                │
│  • index.html            • App.tsx (440 lines)   • fetchCities()           │
│  • index.tsx             • DashboardCharts.tsx   • fetchDashboardData()    │
│  • vite.config.ts        • ETLLogs.tsx           • services/api.ts        │
│                          • types.ts              • Transform API response  │
│  Build: npm run build                                                       │
│  Dev: npm run dev (port 5173)                    Visualizations:          │
│  Type: React 19 + TypeScript                     • TrendsChart (PM2.5,     │
│  Styling: Tailwind CSS                             PM10, rolling avg,     │
│  Icons: Lucide React                               WHO threshold)          │
│  Charts: Recharts                                • CorrelationMatrix      │
│                                                   (Pearson correlation)    │
│                          Views:                   • TrueHeatmap (daily     │
│                          • Dashboard (KPI)         max PM2.5)              │
│                          • QA Report (DQ)        • ETLLogs (system logs)  │
│                          • Data Registry         • Data Registry (table)  │
│                          • Logs                  • Glossary (help)        │
│                          • Glossary (help)                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Данные: Источники

### **1. Open-Meteo Weather API**
- **Endpoint**: `https://api.open-meteo.com/v1/forecast`
- **Parameters**:
  - `latitude`, `longitude`: Coordinates of city
  - `past_days=7`: Fetch 7 days of historical data
  - `forecast_days=1`: Fetch 1 day of forecast
  - `hourly=temperature_2m,relative_humidity_2m,wind_speed_10m`: Metrics
- **Response**: JSON with `hourly` array containing timestamps and measurements
- **Granularity**: Hourly
- **Cost**: Free, no authentication

### **2. Open-Meteo Air Quality API**
- **Endpoint**: `https://air-quality-api.open-meteo.com/v1/air-quality`
- **Parameters**:
  - `latitude`, `longitude`: Coordinates of city
  - `past_days=7`: Fetch 7 days historical
  - `forecast_days=1`: Fetch 1 day forecast
  - `hourly=pm10,pm2_5`: Air quality metrics
- **Response**: JSON with `hourly` array
- **Granularity**: Hourly
- **Cost**: Free, no authentication

### **3. Monitored Cities (13 cities)**

| City | Country | Coordinates | Use Case |
|------|---------|------------|----------|
| Москва | RU | 55.7558, 37.6173 | Reference (Russia, capital) |
| Санкт-Петербург | RU | 59.9343, 30.3351 | Northern Europe comparison |
| Ульяновск | RU | 54.3141, 48.4031 | Mid-Russia |
| Казань | RU | 55.7887, 49.1221 | Volga region |
| Новосибирск | RU | 55.0084, 82.9357 | Siberia |
| Екатеринбург | RU | 56.8389, 60.6057 | Ural region |
| Лондон | GB | 51.5074, -0.1278 | Western Europe |
| Берлин | DE | 52.5200, 13.4050 | Central Europe |
| Париж | FR | 48.8566, 2.3522 | Western Europe |
| Рим | IT | 41.9028, 12.4964 | Southern Europe |
| Пекин | CN | 39.9042, 116.4074 | Asian reference (high pollution) |
| Токио | JP | 35.6762, 139.6503 | Japan (advanced pollution control) |
| Дубай | AE | 25.2048, 55.2708 | Middle East |

---

## 🔍 Extract: Сбор данных

### **Function**: `fetch_open_meteo_data(lat, lng)`

Located in: `services/etl.py` (lines 47-59)

```python
def fetch_open_meteo_data(lat, lng):
    """Запрос данных погоды и качества воздуха за 7 дней"""
    print(f'Запрос данных для координат {lat}, {lng}...')
    
    # 1. Погода
    w_url = f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&past_days=7&forecast_days=1&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m'
    w_res = requests.get(w_url).json()
    
    # 2. Воздух
    aq_url = f'https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lng}&past_days=7&forecast_days=1&hourly=pm10,pm2_5'
    aq_res = requests.get(aq_url).json()
    
    return w_res, aq_res
```

### **Parameters**:
- `lat`, `lng`: City coordinates (from CITIES list)

### **Returns**:
- `w_res`: Weather JSON
- `aq_res`: Air Quality JSON

### **Data Window**:
- Historical: 7 days
- Forecast: 1 day
- **Total**: 8 days × 24 hours = 192 hourly records per city

### **Network Resilience**:
- No built-in retry logic (to be improved)
- Timeout: Default requests timeout
- Error handling: Wrapped in try-except in main()

### **Data Volume**:
- Per city: ~8 KB JSON
- 13 cities: ~104 KB per run
- Frequency: Manual execution (see Scheduling)

---

## 🔄 Transform: Преобразование

### **Functions Chain**:

#### **1. `transform_data(w_data, aq_data)`**
Located: `services/etl.py` (lines 62-88)

**Steps**:
1. Create weather DataFrame from `w_data['hourly']`
   - Columns: `time`, `temperature`, `humidity`, `wind_speed`
2. Create air quality DataFrame from `aq_data['hourly']`
   - Columns: `time`, `pm10`, `pm25`
3. Merge on `time` column (inner join)
   - Result: Single DataFrame with 8 columns
4. Convert `time` string to `timestamp` (ISO format → datetime)
5. **Data Cleaning**:
   - Replace negative PM10 values with NULL (remove outliers)
   - Replace negative PM2.5 values with NULL
   - Rationale: API sometimes returns negative values for missing data

**Output**:
```python
DataFrame {
  time: str (ISO)
  timestamp: datetime
  temperature: float
  humidity: float
  wind_speed: float
  pm10: float (nullable)
  pm25: float (nullable)
}
```

#### **2. `train_and_predict_ml(df)`**
Located: `services/etl.py` (lines 91-122)

**Algorithm**: Linear Regression (sklearn)

**Target**: PM2.5 (predicted_pm25)

**Features**:
- `temperature` (°C): How temperature affects air composition
- `wind_speed` (km/h): Dispersion effect
- `humidity` (%): Moisture affects particle aggregation

**Training**:
1. Drop rows with NaN in [temperature, wind_speed, humidity, pm25]
2. Check minimum 10 samples requirement
3. Fit LinearRegression model
4. Log R² score (model fit quality)

**Prediction**:
1. For rows where features are available (fill NaN with mean)
2. Generate `predicted_pm25` column
3. Round to 2 decimal places

**Why Linear Regression?**
- Interpretable weights (coefficient = feature importance)
- Fast training/prediction
- Suitable for hourly forecasting
- Captures linear relationships in weather-pollution

**Output**:
```python
DataFrame {
  ... (all previous columns)
  predicted_pm25: float (rounded to 2 decimals)
}
```

### **Data Aggregation**:
No aggregation at transform stage. Maintains hourly granularity.

---

## ✅ Validate (DQ): Контроль качества

### **Validation Points**:

Located: `services/etl.py` (implied in main() flow) + `App.tsx` (frontend QA)

#### **1. In ETL (Backend)**:

| Check | Logic | Action |
|-------|-------|--------|
| **Negative PM values** | `if pm10 < 0 or pm25 < 0` | Replace with NULL |
| **Insufficient data for ML** | `if len(train_df) < 10` | Log warning, set predicted_pm25 = NULL |
| **Data merge completeness** | Inner join weather + air | May lose rows if timestamps don't align |

#### **2. In Frontend (App.tsx)**:

**QA Report View** calculates:

```typescript
// 1. Missing data count
const missingPM = data.filter(d => d.pm25 === null).length;
const missingPct = ((missingPM / data.length) * 100).toFixed(1);

// 2. Quality Score
const qualityScore = Math.max(0, 100 - (missingPM / data.length * 100));

// 3. Timestamp monotonicity check
let timestampIssues = 0;
for (let i = 1; i < data.length; i++) {
  const prev = new Date(data[i - 1].timestamp).getTime();
  const curr = new Date(data[i].timestamp).getTime();
  if (curr <= prev) timestampIssues++;
}

// 4. Anomaly detection (spikes > 50%)
let anomalyCount = 0;
for (let i = 1; i < data.length; i++) {
  const change = Math.abs((curr - prev) / prev);
  if (change > 0.5) anomalyCount++;
}

// 5. WHO Threshold Exceedance
const WHO_LIMIT_DAILY = 15 // µg/m³
const daysExceedingWHO = Array.from(dailyMax.values())
  .filter(v => v > WHO_LIMIT_DAILY).length;
```

**QA Metrics Displayed**:
- Total rows: Count of records
- Missing PM2.5: Count + percentage
- Quality Score: 0-100 based on completeness
- Timestamp issues: Monotonicity violations
- Anomalies: Sudden spikes
- Days exceeding WHO: Health risk indicator

### **Quality Standards**:
- **Good**: Quality Score > 95%, Anomalies < 2, Timestamp issues = 0
- **Fair**: Quality Score 80-95%, Anomalies 2-5
- **Poor**: Quality Score < 80%, Manual investigation needed

---

## 📥 Load: Загрузка в БД

### **Function**: `load_to_db(conn, df, city_name, lat, lng, country)`
Located: `services/etl.py` (lines 125-180)

### **Step 1: Upsert City Dimension**

```sql
INSERT INTO dim_city (name, country_code, latitude, longitude)
VALUES (%s, %s, %s, %s)
ON CONFLICT (name) DO NOTHING
RETURNING city_id;
```

**Logic**:
- If city exists: ignore (do nothing)
- If city is new: insert and return city_id
- Fallback: Query city_id from table if insert didn't return

**Table**: `dim_city`
- **city_id** (SERIAL PRIMARY KEY)
- **name** (VARCHAR 100, UNIQUE)
- **country_code** (VARCHAR 5)
- **latitude** (DECIMAL 9,6)
- **longitude** (DECIMAL 9,6)

### **Step 2: Prepare Data**

Convert DataFrame rows to SQL tuples:

```python
for _, row in df.iterrows():
  ts = row['timestamp']
  weather_data.append((city_id, ts, row['temperature'], row['humidity'], row['wind_speed']))
  aq_data.append((city_id, ts, row['pm10'], row['pm25'], row['predicted_pm25']))
```

### **Step 3: Batch Insert Weather**

```sql
INSERT INTO fact_weather (city_id, timestamp, temperature, humidity, wind_speed)
VALUES %s
ON CONFLICT (city_id, timestamp) DO UPDATE
SET temperature=EXCLUDED.temperature, 
    humidity=EXCLUDED.humidity, 
    wind_speed=EXCLUDED.wind_speed;
```

**Table**: `fact_weather`
- **weather_id** (SERIAL PRIMARY KEY)
- **city_id** (INTEGER FK → dim_city)
- **timestamp** (TIMESTAMP)
- **temperature** (DECIMAL 5,2)
- **humidity** (DECIMAL 5,2)
- **wind_speed** (DECIMAL 5,2)
- **created_at** (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- **UNIQUE(city_id, timestamp)** — Prevents duplicates

### **Step 4: Batch Insert Air Quality**

```sql
INSERT INTO fact_air_quality (city_id, timestamp, pm10, pm25, predicted_pm25)
VALUES %s
ON CONFLICT (city_id, timestamp) DO UPDATE
SET pm10=EXCLUDED.pm10, 
    pm25=EXCLUDED.pm25, 
    predicted_pm25=EXCLUDED.predicted_pm25;
```

**Table**: `fact_air_quality`
- **aq_id** (SERIAL PRIMARY KEY)
- **city_id** (INTEGER FK → dim_city)
- **timestamp** (TIMESTAMP)
- **pm10** (DECIMAL 6,2)
- **pm25** (DECIMAL 6,2)
- **predicted_pm25** (DECIMAL 6,2)
- **created_at** (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
- **UNIQUE(city_id, timestamp)** — Prevents duplicates

### **Batch Insert Library**:
- Uses `psycopg2.extras.execute_values()`
- More efficient than individual INSERT statements
- Single statement for all rows
- For 13 cities × 192 hours = 2,496 rows per run

### **Conflict Resolution**:
- Strategy: **Upsert** (Update if exists, Insert if new)
- Rationale: Handles re-runs, data corrections, forecast updates
- Same timestamp + city = overwrite with new data

### **Indexes**:

```sql
CREATE INDEX idx_weather_time ON fact_weather(timestamp);
CREATE INDEX idx_aq_time ON fact_air_quality(timestamp);
```

- Optimize: Filter by timestamp range (API query)
- Optimize: Dashboard query for last 168 rows

---

## 💾 Storage: Витрина данных

### **SQL VIEW**: `dm_dashboard_analytics`

**Purpose**: Provide single query entry point for frontend

**Definition** (from `ecosense.sql`):

```sql
CREATE OR REPLACE VIEW dm_dashboard_analytics AS
SELECT 
    c.name as city_name,
    w.timestamp,
    w.temperature,
    w.humidity,
    w.wind_speed,
    aq.pm10,
    aq.pm25,
    aq.predicted_pm25
FROM fact_weather w
JOIN dim_city c ON w.city_id = c.city_id
LEFT JOIN fact_air_quality aq ON w.city_id = aq.city_id AND w.timestamp = aq.timestamp
ORDER BY w.timestamp DESC;
```

**Join Strategy**:
1. INNER JOIN: `fact_weather` + `dim_city`
   - All weather rows with city name
2. LEFT JOIN: Result + `fact_air_quality`
   - Preserve weather rows even if AQ data is missing
   - Can handle partial data (e.g., weather without AQ)

**Columns** (8 total):
| Column | Source | Type | Nullable |
|--------|--------|------|----------|
| city_name | dim_city.name | VARCHAR | NO |
| timestamp | fact_weather.timestamp | TIMESTAMP | NO |
| temperature | fact_weather.temperature | DECIMAL | YES |
| humidity | fact_weather.humidity | DECIMAL | YES |
| wind_speed | fact_weather.wind_speed | DECIMAL | YES |
| pm10 | fact_air_quality.pm10 | DECIMAL | YES |
| pm25 | fact_air_quality.pm25 | DECIMAL | YES |
| predicted_pm25 | fact_air_quality.predicted_pm25 | DECIMAL | YES |

**Ordering**: Descending by timestamp (newest first)

**Query Cost**:
- Index usage: `idx_weather_time`, `idx_aq_time`
- Full view scan: ~168 rows per city per request
- Typical response time: < 100ms

---

## 🔌 API: REST endpoints

### **Server**: FastAPI (Python)
**File**: `server.py`
**Host**: `0.0.0.0`
**Port**: `8000`
**Docs**: `http://localhost:8000/docs` (Swagger UI)

### **Endpoints**:

#### **1. GET /api/cities**

**Purpose**: Fetch list of monitored cities

**Response**:
```json
{
  "cities": [
    {
      "city_id": 1,
      "name": "Москва",
      "country_code": "RU",
      "latitude": 55.7558,
      "longitude": 37.6173
    },
    ...
  ]
}
```

**Query**:
```sql
SELECT * FROM dim_city ORDER BY name
```

**Error Handling**:
- 500: Database connection error
  - Message: str(exception)

**Used by**: Frontend city selector dropdown

---

#### **2. GET /api/measurements**

**Purpose**: Fetch dashboard data for a specific city

**Query Parameters**:
- `city_name` (required): City name (string)
  - Example: `?city_name=Москва`

**Response**:
```json
{
  "data": [
    {
      "city_name": "Москва",
      "timestamp": "2025-12-25T12:00:00",
      "temperature": 5.2,
      "humidity": 72.5,
      "wind_speed": 8.3,
      "pm10": 45.2,
      "pm25": 18.7,
      "predicted_pm25": 19.3
    },
    ...
  ]
}
```

**Query**:
```sql
SELECT * FROM dm_dashboard_analytics
WHERE city_name = %s
ORDER BY timestamp DESC
LIMIT 168
```

**Limit**: 168 rows (7 days × 24 hours)

**Error Handling**:
- 500: Database error
  - Message: "Данные не найдены. Запустите etl.py"

**Used by**: Dashboard charts, data table

---

#### **3. GET /**

**Purpose**: Health check

**Response**:
```json
{
  "status": "EcoSense API is running"
}
```

**Used by**: Infrastructure monitoring, API availability test

---

### **Middleware**: CORS

```python
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "*"  # For testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Rationale**:
- localhost:3000: React dev server (alternative)
- localhost:5173: Vite dev server (current)
- *: Wildcard for testing

**Note**: Wildcard should be restricted in production

---

### **Data Flow**:

```
Client Request
    ↓
FastAPI route handler
    ↓
get_db_connection() → psycopg2.connect()
    ↓
Execute SQL query on VIEW/TABLE
    ↓
Cursor.fetchall() → RealDictCursor (returns dicts)
    ↓
Format response JSON
    ↓
Return to client
    ↓
Close cursor + connection
```

---

## 🖥️ UI: Фронтенд

### **Framework**: React 19 + TypeScript + Vite

**Entry Point**: `index.html` → `index.tsx` → `App.tsx`

**Build**:
```bash
npm install       # Install dependencies
npm run dev       # Development: http://localhost:5173
npm run build     # Production bundle
npm run preview   # Preview production build
```

### **Main Component**: `App.tsx` (440 lines)

**State**:
```typescript
const [activeView, setActiveView] = useState<'dashboard' | 'qa' | 'data' | 'logs' | 'glossary'>('dashboard');
const [cities, setCities] = useState<City[]>([]);
const [selectedCityName, setSelectedCityName] = useState<string>('');
const [data, setData] = useState<UnifiedDataPoint[]>([]);
const [loading, setLoading] = useState(false);
const [logs, setLogs] = useState<LogEntry[]>([]);
const [showMLForecast, setShowMLForecast] = useState(true);
const [chartMode, setChartMode] = useState<'simple' | 'detailed' | 'weather'>('simple');
```

**Lifecycle**:
1. On mount: `fetchCities()` → populate city selector
2. On city change: `loadData()` → `fetchDashboardData(cityName)`
3. Transform API response → `UnifiedDataPoint[]`
4. Render selected view

### **Views**:

#### **1. Dashboard** 🎯

**Components**:
- **KPI Cards**:
  - Current PM2.5 (last value)
  - Current Temperature
  - Current Humidity
  - Days exceeding WHO threshold
  - Quality Score (%)
  - Missing data count

- **Charts** (Recharts):
  - **TrendsChart**: 
    - PM2.5 (area)
    - PM10 (optional)
    - Rolling average (6-hour)
    - WHO threshold line (15 µg/m³)
    - AI prediction (dashed line)
    - Features: `simple | detailed | weather` modes
    
  - **CorrelationMatrix**:
    - 4×4 matrix (PM2.5, Temperature, Wind, Humidity)
    - Pearson correlation coefficients
    - Color-coded: red (positive) to blue (negative)
    
  - **TrueHeatmap**:
    - Daily max PM2.5 by day
    - Heatmap colors: green (good) to red (bad)

**Calculations**:
```typescript
// stats object
const stats = useMemo(() => {
  // 1. Days exceeding WHO
  const dailyMax = new Map<string, number>();
  data.forEach(d => { /* calculate daily max */ });
  const daysExceedingWHO = Array.from(dailyMax.values())
    .filter(v => v > WHO_LIMIT_DAILY).length;
  
  // 2. Missing data
  const missingPM = data.filter(d => d.pm25 === null).length;
  const qualityScore = Math.max(0, 100 - (missingPM / data.length * 100));
  
  // 3. Timestamp issues
  let timestampIssues = 0;
  for (let i = 1; i < data.length; i++) {
    if (curr_ts <= prev_ts) timestampIssues++;
  }
  
  // 4. Anomalies
  let anomalyCount = 0;
  for (let i = 1; i < data.length; i++) {
    if (change > 0.5) anomalyCount++;
  }
  
  return { current, daysExceedingWHO, ..., anomalyCount };
}, [data]);
```

#### **2. QA Report** 📋

**Purpose**: Data quality assessment

**Displays**:
- Total rows
- Missing PM2.5 count & percentage
- Quality Score (%)
- Timestamp monotonicity issues
- Anomaly count (spikes > 50%)
- Days exceeding WHO limit
- ML model R² (if available)

**Interpretation**:
- Green: Score > 95%
- Yellow: 80-95%
- Red: < 80%

#### **3. Data Registry** 📊

**Purpose**: Browse raw measurements

**Columns**:
- Timestamp
- PM2.5, PM10
- Temperature, Humidity, Wind Speed
- Predicted PM2.5
- Freshness indicator

**Features**:
- Sortable table
- Scrollable (last 168 rows)
- Shows data freshness

#### **4. Logs** 📝

**Purpose**: System operation history

**Log Types**:
- `info`: General messages
- `success`: Operation completed
- `error`: Error occurred
- `warning`: Data quality issue

**Format**: `[HH:MM:SS] TYPE: Message`

**Events Logged**:
- ETL run start/completion
- API errors
- Data load success/failure
- City selection
- QA validation results

#### **5. Glossary** ℹ️

**Purpose**: Help documentation

**Contents**:
- Metric definitions (PM2.5, PM10, WHO standards)
- API explanation
- ETL pipeline overview
- Data sources
- Links to documentation

---

### **API Client**: `services/api.ts`

```typescript
const BACKEND_URL = 'http://localhost:8000/api';

export const fetchCities = async (): Promise<City[]> => {
  const response = await fetch(`${BACKEND_URL}/cities`);
  if (!response.ok) throw new Error('Ошибка загрузки городов с сервера');
  const data = await response.json();
  return data.cities.map((c: any) => ({
    name: c.name,
    lat: c.latitude,
    lng: c.longitude,
    country: c.country_code
  }));
};

export const fetchDashboardData = async (cityName: string): Promise<UnifiedDataPoint[]> => {
  const response = await fetch(`${BACKEND_URL}/measurements?city_name=${encodeURIComponent(cityName)}`);
  if (!response.ok) throw new Error(`Ошибка сервера: ${response.statusText}`);
  const json = await response.json();
  
  return json.data.map((row: any) => ({
    timestamp: row.timestamp,
    displayTime: new Date(row.timestamp).toLocaleDateString('ru-RU', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
    }),
    pm10: row.pm10,
    pm25: row.pm25,
    temperature: row.temperature,
    windSpeed: row.wind_speed,
    humidity: row.humidity,
    predictedPM25: row.predicted_pm25
  }));
};
```

---

## ⏰ Scheduling & Monitoring

### **Current State**: Manual execution

```bash
python services/etl.py
```

**When to run**:
- After database initialization
- On-demand data refresh
- Development testing

### **Recommended**: Scheduled execution

**Option 1: Cron Job** (Linux/macOS)
```bash
# Run every hour
0 * * * * cd /path/to/project && python services/etl.py

# Run every 6 hours
0 */6 * * * cd /path/to/project && python services/etl.py
```

**Option 2: Celery** (Python task queue)
```python
from celery import Celery
from celery.schedules import crontab

app = Celery('ecosense')
app.conf.beat_schedule = {
    'run-etl-every-6-hours': {
        'task': 'services.etl.main',
        'schedule': crontab(minute=0, hour='*/6'),
    },
}
```

**Option 3: APScheduler** (Python)
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(main, 'interval', hours=6)
scheduler.start()
```

**Option 4: Docker + Kubernetes**
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: ecosense-etl
spec:
  schedule: "0 */6 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: etl
            image: ecosense:latest
            command: ["python", "services/etl.py"]
          restartPolicy: OnFailure
```

### **Recommended Frequency**: Every 6 hours
- Captures data variations
- Reduces API calls vs. hourly
- Provides adequate freshness for analytics

### **Monitoring**:

**Metrics to Track**:
1. **Last run time**: When ETL last completed
2. **Run duration**: How long the ETL takes
3. **Data freshness**: Max(timestamp in DB) - now()
4. **Success rate**: Successful runs / total runs
5. **Errors**: Failed city extractions, DB connection issues
6. **Data quality**: Quality score trend

**Logging**:

Current (basic):
```python
print(f'Запрос данных для координат {lat}, {lng}...')
print(f'Данные для {city_name} сохранены в БД.')
print("ETL Пайплайн завершен успешно.")
```

**Recommended** (structured):
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('etl.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Usage
logger.info(f"ETL started for {city['name']}")
logger.error(f"Failed to fetch {city['name']}: {str(e)}")
logger.info(f"ETL completed in {elapsed_time}s")
```

---

## ⚠️ Error Handling & Retry Logic

### **Current Implementation**: Minimal

```python
def main():
    conn = get_db_connection()
    if not conn:
        return

    for city in CITIES:
        try:
            # ETL Pipeline
            w, aq = fetch_open_meteo_data(city['lat'], city['lng'])
            df = transform_data(w, aq)
            df = train_and_predict_ml(df)
            load_to_db(conn, df, city['name'], city['lat'], city['lng'], city['country'])
        except Exception as e:
            print(f"Ошибка обработки города {city['name']}: {e}")

    conn.close()
```

**Issues**:
- No retry logic on API failures
- Single exception catches all errors
- No rollback on partial failures
- No timeout handling

### **Recommended Improvements**:

#### **1. API Call Retry (Exponential Backoff)**

```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_session():
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,  # 0.5s, 1s, 2s
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
        logger.error(f"Timeout for {lat},{lng}")
        raise
    except requests.RequestException as e:
        logger.error(f"API error: {e}")
        raise
```

#### **2. Database Connection Retry**

```python
def get_db_connection(max_retries=3):
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            return conn
        except psycopg2.OperationalError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(f"DB connection failed, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to connect to DB after {max_retries} attempts")
                raise
```

#### **3. Transaction Rollback on Error**

```python
def load_to_db(conn, df, city_name, lat, lng, country):
    try:
        cur = conn.cursor()
        
        # Upsert city
        cur.execute(...)
        city_id = ...
        
        # Batch inserts
        execute_values(cur, insert_weather_query, weather_data)
        execute_values(cur, insert_aq_query, aq_data)
        
        conn.commit()
        logger.info(f"Данные для {city_name} успешно сохранены")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error loading {city_name}: {e}")
        raise
    finally:
        cur.close()
```

#### **4. Partial Failure Handling**

```python
def main():
    conn = get_db_connection()
    failed_cities = []
    
    for city in CITIES:
        try:
            w, aq = fetch_open_meteo_data(city['lat'], city['lng'])
            df = transform_data(w, aq)
            df = train_and_predict_ml(df)
            load_to_db(conn, df, city['name'], city['lat'], city['lng'], city['country'])
            logger.info(f"✓ {city['name']}")
            
        except Exception as e:
            logger.error(f"✗ {city['name']}: {e}")
            failed_cities.append(city['name'])
    
    conn.close()
    
    if failed_cities:
        logger.warning(f"Failed cities: {', '.join(failed_cities)}")
        # Send alert/email
    else:
        logger.info("✓ All cities processed successfully")
```

#### **5. Data Validation Before Load**

```python
def validate_data(df):
    """Validation before database insert"""
    issues = []
    
    # Check timestamp range
    if df['timestamp'].isna().any():
        issues.append("Null timestamps found")
    
    # Check value ranges
    if (df['temperature'] < -50).any() or (df['temperature'] > 60).any():
        issues.append("Temperature out of realistic range")
    
    if (df['pm25'] < 0).any():
        issues.append("Negative PM2.5 values (should be filtered)")
    
    if df.shape[0] < 100:
        issues.append(f"Only {df.shape[0]} rows (expected ~192)")
    
    if issues:
        raise ValueError("Data validation failed: " + "; ".join(issues))
    
    return True
```

---

## 📋 Summary Table: Complete Pipeline

| Stage | Component | Technology | Input | Output | Frequency | Error Handling |
|-------|-----------|-----------|-------|--------|-----------|-----------------|
| **Extract** | fetch_open_meteo_data | requests | City coords | JSON (weather, AQ) | Manual / 6h | Generic try-catch |
| **Transform** | transform_data + train_and_predict_ml | pandas, sklearn | JSON | DataFrame + ML predictions | Inline (per batch) | NaN removal |
| **Validate** | Implicit checks | Python logic | DataFrame | Warnings/logs | Inline | Log only |
| **Load** | load_to_db | psycopg2 + execute_values | DataFrame | Rows in DB | Inline | Rollback on error |
| **Storage** | PostgreSQL + VIEW | pg | Fact/Dim tables | dm_dashboard_analytics | Persistent | Constraints + indexes |
| **API** | FastAPI server | Python | HTTP requests | JSON responses | Real-time | 500 error responses |
| **UI** | React + Recharts | TypeScript | /api/cities, /api/measurements | Interactive charts | On demand | User-facing error messages |

---

## 🚀 Deployment Checklist

- [ ] PostgreSQL configured with correct tables (ecosense.sql applied)
- [ ] Python virtual environment created
- [ ] `requirements.txt` installed
- [ ] ETL run once successfully (`python services/etl.py`)
- [ ] FastAPI server starts (`python server.py`)
- [ ] Frontend dependencies installed (`npm install`)
- [ ] Frontend dev server starts (`npm run dev`)
- [ ] Health check passes (`GET http://localhost:8000/`)
- [ ] Cities endpoint works (`GET http://localhost:8000/api/cities`)
- [ ] Dashboard loads data for a city (`GET http://localhost:8000/api/measurements?city_name=Москва`)
- [ ] React UI displays charts without errors
- [ ] Scheduled job configured (cron/Celery/APScheduler)
- [ ] Logs directory configured
- [ ] Database backups scheduled

---

## 📚 References

- **Open-Meteo API**: https://open-meteo.com/
- **WHO Air Quality Standards**: https://www.who.int/publications/i/item/9789240034228
- **FastAPI**: https://fastapi.tiangolo.com/
- **React**: https://react.dev/
- **PostgreSQL**: https://www.postgresql.org/
- **Recharts**: https://recharts.org/
- **Scikit-learn**: https://scikit-learn.org/

---

**Document Version**: 1.0  
**Last Updated**: 2025-12-25  
**Maintained By**: EcoSense Team
