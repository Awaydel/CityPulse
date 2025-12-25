from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = FastAPI(title="EcoSense API")

# Настройка CORS (разрешаем запросы с React)
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "*"  # Для тестов
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Конфигурация БД
DB_CONFIG = {
    'dbname': 'ecosense',
    'user': 'postgres',
    'password': '123',
    'host': '127.0.0.1',
    'port': 5432
}

def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

@app.get("/")
def read_root():
    return {"status": "EcoSense API is running"}

@app.get("/api/cities")
def get_cities():
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

@app.get("/api/measurements")
def get_measurements(city_name: str = Query(..., description="Название города")):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Используем VIEW, который мы создали в schema.json
        query = """
            SELECT * FROM dm_dashboard_analytics
            WHERE city_name = %s
            ORDER BY timestamp DESC
            LIMIT 168 -- 7 дней по 24 часа
        """

        cur.execute(query, (city_name,))
        data = cur.fetchall()

        cur.close()
        conn.close()

        if not data:
            return {"data": [], "message": "Данные не найдены. Запустите etl.py"}

        return {"data": data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
