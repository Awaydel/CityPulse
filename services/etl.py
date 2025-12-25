import requests
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import psycopg2
from psycopg2.extras import execute_values
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# --- КОНФИГУРАЦИЯ ---
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'ecosense'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '123'),
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': os.getenv('DB_PORT', '5432')
}

STAGING_DIR = 'staging'
os.makedirs(STAGING_DIR, exist_ok=True)

CITIES = [
    # Россия
    {'name': 'Москва',          'lat': 55.7558, 'lng': 37.6173,  'country': 'RU'},
    {'name': 'Санкт-Петербург', 'lat': 59.9343, 'lng': 30.3351,  'country': 'RU'},
    {'name': 'Ульяновск',       'lat': 54.3141, 'lng': 48.4031,  'country': 'RU'},
    {'name': 'Казань',          'lat': 55.7887, 'lng': 49.1221,  'country': 'RU'},
    {'name': 'Новосибирск',     'lat': 55.0084, 'lng': 82.9357,  'country': 'RU'},
    {'name': 'Екатеринбург',    'lat': 56.8389, 'lng': 60.6057,  'country': 'RU'},
    # Европа
    {'name': 'Лондон',          'lat': 51.5074, 'lng': -0.1278,  'country': 'GB'},
    {'name': 'Берлин',          'lat': 52.5200, 'lng': 13.4050,  'country': 'DE'},
    {'name': 'Париж',           'lat': 48.8566, 'lng': 2.3522,   'country': 'FR'},
    {'name': 'Рим',             'lat': 41.9028, 'lng': 12.4964,  'country': 'IT'},
    # Азия
    {'name': 'Пекин',           'lat': 39.9042, 'lng': 116.4074, 'country': 'CN'},
    {'name': 'Токио',           'lat': 35.6762, 'lng': 139.6503, 'country': 'JP'},
    {'name': 'Дубай',           'lat': 25.2048, 'lng': 55.2708,  'country': 'AE'},
]

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f'Ошибка подключения к БД: {e}')
        return None

def fetch_open_meteo_data(lat, lng):
    """Запрос данных погоды и качества воздуха за 7 дней"""
    print(f'Запрос данных для координат {lat}, {lng}...')
    
    # 1. Погода
    w_url = f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&past_days=7&forecast_days=1&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m'
    try:
        w_res = requests.get(w_url, timeout=10).json()
    except Exception as e:
        print(f"Ошибка запроса погоды: {e}")
        w_res = {}

    # 2. Воздух
    aq_url = f'https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lng}&past_days=7&forecast_days=1&hourly=pm10,pm2_5'
    try:
        aq_res = requests.get(aq_url, timeout=10).json()
    except Exception as e:
        print(f"Ошибка запроса воздуха: {e}")
        aq_res = {}
    
    return w_res, aq_res

def transform_data(w_data, aq_data):
    """Преобразование JSON в DataFrame и объединение"""
    # Проверка на пустые данные
    if 'hourly' not in w_data or 'hourly' not in aq_data:
        return pd.DataFrame()

    # Создаем DataFrame погоды
    df_w = pd.DataFrame({
        'time': w_data['hourly']['time'],
        'temperature': w_data['hourly']['temperature_2m'],
        'humidity': w_data['hourly']['relative_humidity_2m'],
        'wind_speed': w_data['hourly']['wind_speed_10m']
    })
    
    # Создаем DataFrame воздуха
    df_aq = pd.DataFrame({
        'time': aq_data['hourly']['time'],
        'pm10': aq_data['hourly']['pm10'],
        'pm25': aq_data['hourly']['pm2_5']
    })
    
    # Объединяем по времени
    df = pd.merge(df_w, df_aq, on='time', how='inner')
    
    # Очистка
    df['timestamp'] = pd.to_datetime(df['time'])
    
    # Удаляем аномалии (отрицательные значения)
    df.loc[df['pm10'] < 0, 'pm10'] = None
    df.loc[df['pm25'] < 0, 'pm25'] = None
    
    return df

def train_and_predict_ml(df):
    """Обучение линейной регрессии для предсказания PM2.5"""
    if df.empty:
        return df

    # Подготовка данных для обучения (убираем NaN)
    train_df = df.dropna(subset=['temperature', 'wind_speed', 'humidity', 'pm25'])
    
    if len(train_df) < 10:
        print('Недостаточно данных для ML')
        df['predicted_pm25'] = None
        return df

    X = train_df[['temperature', 'wind_speed', 'humidity']]
    y = train_df['pm25']
    
    model = LinearRegression()
    model.fit(X, y)
    
    print(f'ML Модель обучена. R2 Score: {model.score(X, y):.2f}')
    
    # Предсказание
    X_full = df[['temperature', 'wind_speed', 'humidity']].fillna(train_df[['temperature', 'wind_speed', 'humidity']].mean())
    
    df['predicted_pm25'] = model.predict(X_full)
    df['predicted_pm25'] = df['predicted_pm25'].round(2)
    
    return df

def load_to_db(conn, df, city_name, lat, lng, country):
    if df.empty:
        return

    cur = conn.cursor()

    # 1. Обновляем справочник городов
    cur.execute("""
        INSERT INTO dim_city (name, country_code, latitude, longitude)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (name) DO NOTHING
        RETURNING city_id;
    """, (city_name, country, lat, lng))

    result = cur.fetchone()
    if result:
        city_id = result[0]
    else:
        cur.execute("SELECT city_id FROM dim_city WHERE name = %s", (city_name,))
        res = cur.fetchone()
        if res:
            city_id = res[0]
        else:
            print(f"Ошибка: Не удалось получить ID для города {city_name}")
            return
    
    # 2. Загружаем факты
    weather_data = []
    aq_data = []
    
    for _, row in df.iterrows():
        ts = row['timestamp']
        weather_data.append((city_id, ts, row['temperature'], row['humidity'], row['wind_speed']))
        aq_data.append((city_id, ts, row['pm10'], row['pm25'], row['predicted_pm25']))

    insert_weather_query = """
        INSERT INTO fact_weather (city_id, timestamp, temperature, humidity, wind_speed)
        VALUES %s
        ON CONFLICT (city_id, timestamp) DO UPDATE
        SET temperature=EXCLUDED.temperature, humidity=EXCLUDED.humidity, wind_speed=EXCLUDED.wind_speed;
    """

    insert_aq_query = """
        INSERT INTO fact_air_quality (city_id, timestamp, pm10, pm25, predicted_pm25)
        VALUES %s
        ON CONFLICT (city_id, timestamp) DO UPDATE
        SET pm10=EXCLUDED.pm10, pm25=EXCLUDED.pm25, predicted_pm25=EXCLUDED.predicted_pm25;
    """
    
    execute_values(cur, insert_weather_query, weather_data)
    execute_values(cur, insert_aq_query, aq_data)
    
    conn.commit()
    cur.close()
    print(f'Данные для {city_name} сохранены в БД.')

# --- AIRFLOW FUNCTIONS ---

def extract_all():
    """Extract step: Fetch data for all cities and save to staging."""
    raw_data = []
    for city in CITIES:
        w, aq = fetch_open_meteo_data(city['lat'], city['lng'])
        raw_data.append({
            'city': city,
            'weather': w,
            'air_quality': aq
        })
    
    with open(f'{STAGING_DIR}/raw_data.json', 'w', encoding='utf-8') as f:
        json.dump(raw_data, f, ensure_ascii=False, default=str)
    print("Extract завершен.")

def transform_all():
    """Transform step: Read staging, transform, ML, save parquet."""
    with open(f'{STAGING_DIR}/raw_data.json', 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    transformed_records = []
    
    for item in raw_data:
        city = item['city']
        w = item['weather']
        aq = item['air_quality']
        
        df = transform_data(w, aq)
        df = train_and_predict_ml(df)
        
        if not df.empty:
            # Сериализуем df обратно в dict для сохранения (или pickle)
            # Для надежности сохраним как JSON-совместимый dict с датами как строки
            df['timestamp'] = df['timestamp'].astype(str)
            records = df.to_dict(orient='records')
            transformed_records.append({
                'city': city,
                'data': records
            })

    with open(f'{STAGING_DIR}/transformed_data.json', 'w', encoding='utf-8') as f:
        json.dump(transformed_records, f, ensure_ascii=False)
    print("Transform завершен.")

def validate_all():
    """Validate step: Check data quality."""
    with open(f'{STAGING_DIR}/transformed_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not data:
        raise ValueError("Валидация: Нет данных для обработки!")
    
    total_records = 0
    for item in data:
        records = item['data']
        total_records += len(records)
        for row in records:
            if row['pm25'] is not None and row['pm25'] < 0:
                 raise ValueError(f"Валидация: Отрицательный PM2.5 в городе {item['city']['name']}")
    
    print(f"Валидация успешна. Обработано записей: {total_records}")

def load_all():
    """Load step: Load data into PostgreSQL."""
    with open(f'{STAGING_DIR}/transformed_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    conn = get_db_connection()
    if not conn:
        raise ConnectionError("Не удалось подключиться к БД")
    
    for item in data:
        city = item['city']
        records = item['data']
        if not records:
            continue
            
        df = pd.DataFrame(records)
        # Восстанавливаем типы
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        load_to_db(conn, df, city['name'], city['lat'], city['lng'], city['country'])
    
    conn.close()
    print("Load завершен.")

def main():
    print("Запуск ETL Pipeline (Standalone)...")
    extract_all()
    transform_all()
    validate_all()
    load_all()
    print("ETL Pipeline завершен.")

if __name__ == '__main__':
    main()
