from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI(title="EcoSense API", description="API для мониторинга качества воздуха", version="2.1.0")

# --- PYDANTIC MODELS (Validation & Documentation) ---
class City(BaseModel):
    city_id: int
    name: string
    country_code: str
    latitude: float
    longitude: float

class Measurement(BaseModel):
    city_name: str
    timestamp: datetime
    temperature: Optional[float]
    humidity: Optional[float]
    wind_speed: Optional[float]
    pm10: Optional[float]
    pm25: Optional[float]
    predicted_pm25: Optional[float]

class CityListResponse(BaseModel):
    cities: List[City]

class MeasurementListResponse(BaseModel):
    data: List[Measurement]
    message: Optional[str] = None

# --- CONFIG ---
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "*" 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    'dbname': 'ecosense',
    'user': 'postgres',
    'password': '123',
    'host': '127.0.0.1',
    'port': 5432
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

# --- ENDPOINTS ---

@app.get("/", tags=["Health"])
def read_root():
    return {"status": "EcoSense API is running", "version": "2.1.0"}

@app.get("/api/cities", response_model=CityListResponse, tags=["Geodata"])
def get_cities():
    """Получение списка отслеживаемых городов"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM dim_city ORDER BY name")
        cities = cur.fetchall()
        cur.close()
        conn.close()
        return {"cities": cities}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/measurements", response_model=MeasurementListResponse, tags=["Analytics"])
def get_measurements(city_name: str = Query(..., description="Название города, например 'Москва'")):
    """
    Получение исторических и предсказанных данных.
    Возвращает последние 168 часов (7 дней).
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT * FROM dm_dashboard_analytics
            WHERE city_name = %s
            ORDER BY timestamp DESC
            LIMIT 168
        """

        cur.execute(query, (city_name,))
        data = cur.fetchall()

        cur.close()
        conn.close()

        if not data:
            return {"data": [], "message": f"Данные для города '{city_name}' не найдены. Запустите ETL."}

        return {"data": data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
