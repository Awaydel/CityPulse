import requests
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import psycopg2
from psycopg2.extras import execute_values
import json
from datetime import datetime
import logging

# --- LOGGING CONFIG ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- КОНФИГУРАЦИЯ ---
DB_CONFIG = {
    'dbname': 'ecosense',
    'user': 'postgres',
    'password': '123',
    'host': '127.0.0.1',
    'port': 5432
}

CITIES = [
    {'name': 'Москва',      'lat': 55.7558, 'lng': 37.6173, 'country': 'RU'},
    {'name': 'Ульяновск',   'lat': 54.3141, 'lng': 48.4031, 'country': 'RU'},
    {'name': 'Лондон',      'lat': 51.5074, 'lng': -0.1278, 'country': 'GB'},
    {'name': 'Берлин',      'lat': 52.52,   'lng': 13.405,  'country': 'DE'}
]

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f'Critical: Ошибка подключения к БД: {e}')
        return None

def fetch_open_meteo_data(lat, lng):
    """Запрос данных погоды и качества воздуха за 7 дней"""
    logger.info(f'Fetching data for coords {lat}, {lng}...')
    
    # 1. Погода
    w_url = f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&past_days=7&forecast_days=1&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m'
    w_res = requests.get(w_url).json()
    
    # 2. Воздух
    aq_url = f'https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lng}&past_days=7&forecast_days=1&hourly=pm10,pm2_5'
    aq_res = requests.get(aq_url).json()
    
    return w_res, aq_res

def transform_data(w_data, aq_data):
    """Преобразование JSON в DataFrame и объединение"""
    try:
        df_w = pd.DataFrame({
            'time': w_data['hourly']['time'],
            'temperature': w_data['hourly']['temperature_2m'],
            'humidity': w_data['hourly']['relative_humidity_2m'],
            'wind_speed': w_data['hourly']['wind_speed_10m']
        })
        
        df_aq = pd.DataFrame({
            'time': aq_data['hourly']['time'],
            'pm10': aq_data['hourly']['pm10'],
            'pm25': aq_data['hourly']['pm2_5']
        })
        
        df = pd.merge(df_w, df_aq, on='time', how='inner')
        df['timestamp'] = pd.to_datetime(df['time'])
        
        # DQ: Удаляем аномалии
        df.loc[df['pm10'] < 0, 'pm10'] = None
        df.loc[df['pm25'] < 0, 'pm25'] = None
        
        return df
    except Exception as e:
        logger.error(f"Transform Error: {e}")
        raise e

def train_and_predict_ml(df):
    """Обучение линейной регрессии для предсказания PM2.5"""
    train_df = df.dropna(subset=['temperature', 'wind_speed', 'humidity', 'pm25'])
    
    if len(train_df) < 10:
        logger.warning('Недостаточно данных для обучения ML модели (<10 строк)')
        df['predicted_pm25'] = None
        return df

    X = train_df[['temperature', 'wind_speed', 'humidity']]
    y = train_df['pm25']
    
    model = LinearRegression()
    model.fit(X, y)
    
    r2 = model.score(X, y)
    logger.info(f'ML Model Trained. R2 Score: {r2:.2f}')
    
    # --- QUALITY GATE ---
    if r2 < 0.3:
        logger.warning(f"Quality Check Failed: Model accuracy is very low (R2={r2:.2f}). Predictions may be unreliable.")

    X_full = df[['temperature', 'wind_speed', 'humidity']].fillna(train_df[['temperature', 'wind_speed', 'humidity']].mean())
    
    df['predicted_pm25'] = model.predict(X_full)
    df['predicted_pm25'] = df['predicted_pm25'].round(2)
    
    return df

def load_to_db(conn, df, city_name, lat, lng, country):
    cur = conn.cursor()

    # 1. Города
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
        city_id = cur.fetchone()[0]
    
    # 2. Факты
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
    logger.info(f'Data committed to DB for {city_name}')

def main():
    conn = get_db_connection()
    if not conn:
        return

    logger.info("Starting ETL Pipeline...")

    for city in CITIES:
        try:
            w, aq = fetch_open_meteo_data(city['lat'], city['lng'])
            df = transform_data(w, aq)
            df = train_and_predict_ml(df)
            load_to_db(conn, df, city['name'], city['lat'], city['lng'], city['country'])
        except Exception as e:
            logger.error(f"Failed processing {city['name']}: {e}")

    conn.close()
    logger.info("ETL Pipeline Finished.")

if __name__ == '__main__':
    main()
