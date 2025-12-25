import requests
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import psycopg2
from psycopg2.extras import execute_values
import json
from datetime import datetime

# --- КОНФИГУРАЦИЯ ---
# Замените эти данные на ваши настройки PostgreSQL
DB_CONFIG = {
    'dbname': 'ecosense',
    'user': 'postgres',
    'password': '123',
    'host': '127.0.0.1',
    'port': 5432
}

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
    w_res = requests.get(w_url).json()
    
    # 2. Воздух
    aq_url = f'https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lng}&past_days=7&forecast_days=1&hourly=pm10,pm2_5'
    aq_res = requests.get(aq_url).json()
    
    return w_res, aq_res

def transform_data(w_data, aq_data):
    """Преобразование JSON в DataFrame и объединение"""
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
    # Open-Meteo возвращает ISO время, можно использовать его как ключ
    df = pd.merge(df_w, df_aq, on='time', how='inner')
    
    # Очистка (удаление пропусков для обучения)
    df['timestamp'] = pd.to_datetime(df['time'])
    
    # Удаляем аномалии (отрицательные значения загрязнения)
    df.loc[df['pm10'] < 0, 'pm10'] = None
    df.loc[df['pm25'] < 0, 'pm25'] = None
    
    return df

def train_and_predict_ml(df):
    """Обучение линейной регрессии для предсказания PM2.5"""
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
    
    # Предсказание для всех строк (даже где pm25 известен, для сравнения, или где пропущен)
    # Заполняем NaN в признаках средними, чтобы модель не упала (упрощение)
    X_full = df[['temperature', 'wind_speed', 'humidity']].fillna(train_df[['temperature', 'wind_speed', 'humidity']].mean())
    
    df['predicted_pm25'] = model.predict(X_full)
    df['predicted_pm25'] = df['predicted_pm25'].round(2)
    
    return df

def load_to_db(conn, df, city_name, lat, lng, country):
    cur = conn.cursor()

    # 1. Обновляем справочник городов (Upsert)
    cur.execute("""
        INSERT INTO dim_city (name, country_code, latitude, longitude)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (name) DO NOTHING
        RETURNING city_id;
    """, (city_name, country, lat, lng))

    # Получаем city_id
    result = cur.fetchone()
    if result:
        city_id = result[0]
    else:
        # Город уже существует, получаем его ID
        cur.execute("SELECT city_id FROM dim_city WHERE name = %s", (city_name,))
        city_id = cur.fetchone()[0]
    
    # 2. Загружаем факты погоды
    weather_data = []
    aq_data = []
    
    for _, row in df.iterrows():
        ts = row['timestamp']
        # Данные погоды
        weather_data.append((city_id, ts, row['temperature'], row['humidity'], row['wind_speed']))
        # Данные воздуха
        aq_data.append((city_id, ts, row['pm10'], row['pm25'], row['predicted_pm25']))

    # Используем execute_values для быстрого insert batch
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
    print("ETL Пайплайн завершен успешно.")

if __name__ == '__main__':
    main()
