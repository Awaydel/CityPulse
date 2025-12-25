from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import math

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

from dotenv import load_dotenv

load_dotenv()

# Конфигурация БД
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'ecosense'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '123'),
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': os.getenv('DB_PORT', '5432')
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

@app.get("/api/analytics/correlation")
def get_correlation_matrix():
    """
    Вычисляет матрицу корреляции Пирсона между погодными условиями и качеством воздуха.
    (Реализация без Pandas для стабильности)
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        query = "SELECT temperature, humidity, wind_speed, pm10, pm25 FROM dm_dashboard_analytics"
        cur.execute(query)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            return {"message": "Недостаточно данных для корреляционного анализа"}
            
        # Преобразуем список словарей в список списков значений для нужных колонок
        columns = ['temperature', 'humidity', 'wind_speed', 'pm10', 'pm25']
        data = {col: [] for col in columns}
        
        for row in rows:
            # Пропускаем строки с None (аналог dropna)
            if any(row[col] is None for col in columns):
                continue
            for col in columns:
                data[col].append(float(row[col]))
        
        n = len(data['temperature'])
        if n < 2:
             return {"message": "Недостаточно полных данных для корреляции"}

        # Функция для расчета корреляции двух списков
        def calculate_pearson(x, y):
            avg_x = sum(x) / n
            avg_y = sum(y) / n
            
            numerator = sum((xi - avg_x) * (yi - avg_y) for xi, yi in zip(x, y))
            sum_sq_diff_x = sum((xi - avg_x) ** 2 for xi in x)
            sum_sq_diff_y = sum((yi - avg_y) ** 2 for yi in y)
            
            if sum_sq_diff_x == 0 or sum_sq_diff_y == 0:
                return None
                
            return numerator / math.sqrt(sum_sq_diff_x * sum_sq_diff_y)

        # Строим матрицу
        matrix = {}
        for col1 in columns:
            matrix[col1] = {}
            for col2 in columns:
                if col1 == col2:
                    matrix[col1][col2] = 1.0
                else:
                    corr = calculate_pearson(data[col1], data[col2])
                    matrix[col1][col2] = corr

        return {"matrix": matrix}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
