import pytest
import psycopg2
import pandas as pd
from datetime import datetime
from services.etl import load_to_db, DB_CONFIG

# --- Test Config ---
TEST_CITY_NAME = "IntegrationTestCity"
TEST_COUNTRY_CODE = "IT"
TEST_LAT = 10.0
TEST_LNG = 20.0

@pytest.fixture(scope="module")
def db_connection():
    """Создает подключение к реальной БД и удаляет тестовые данные после завершения"""
    conn = psycopg2.connect(**DB_CONFIG)
    yield conn
    
    # Cleanup after tests
    cur = conn.cursor()
    cur.execute("DELETE FROM fact_weather WHERE city_id IN (SELECT city_id FROM dim_city WHERE name = %s)", (TEST_CITY_NAME,))
    cur.execute("DELETE FROM fact_air_quality WHERE city_id IN (SELECT city_id FROM dim_city WHERE name = %s)", (TEST_CITY_NAME,))
    cur.execute("DELETE FROM dim_city WHERE name = %s", (TEST_CITY_NAME,))
    conn.commit()
    cur.close()
    conn.close()

def test_db_roundtrip(db_connection):
    """
    Интеграционный тест:
    1. Создаем DataFrame
    2. Загружаем в реальную БД через load_to_db
    3. Читаем из БД
    4. Сверяем данные
    """
    # 1. Prepare Data
    ts = datetime(2025, 1, 1, 12, 0, 0)
    df_data = {
        'timestamp': [ts],
        'temperature': [25.5],
        'humidity': [60.0],
        'wind_speed': [5.5],
        'pm10': [15.0],
        'pm25': [7.0],
        'predicted_pm25': [7.2]
    }
    df = pd.DataFrame(df_data)
    
    # 2. Insert to DB
    # Note: load_to_db handles city creation internally
    load_to_db(db_connection, df, TEST_CITY_NAME, TEST_LAT, TEST_LNG, TEST_COUNTRY_CODE)
    
    # 3. Read back
    cur = db_connection.cursor()
    
    # Get City ID
    cur.execute("SELECT city_id FROM dim_city WHERE name = %s", (TEST_CITY_NAME,))
    city_id = cur.fetchone()[0]
    assert city_id is not None
    
    # Get Weather Fact
    cur.execute(
        "SELECT temperature, humidity, wind_speed FROM fact_weather WHERE city_id = %s AND timestamp = %s",
        (city_id, ts)
    )
    w_row = cur.fetchone()
    assert w_row is not None
    # Check types (psycopg2 might return Decimal for numeric, float for float8)
    assert float(w_row[0]) == 25.5
    assert float(w_row[1]) == 60.0
    
    # Get Air Quality Fact
    cur.execute(
        "SELECT pm10, pm25, predicted_pm25 FROM fact_air_quality WHERE city_id = %s AND timestamp = %s",
        (city_id, ts)
    )
    aq_row = cur.fetchone()
    assert aq_row is not None
    assert float(aq_row[0]) == 15.0
    assert float(aq_row[1]) == 7.0
    assert float(aq_row[2]) == 7.2
    
    cur.close()

def test_db_constraints_unique(db_connection):
    """
    Интеграционный тест: Проверка работу UPSERT (ON CONFLICT).
    Повторная вставка с тем же временем должна обновить данные, а не упасть.
    """
    ts = datetime(2025, 1, 1, 12, 0, 0) # Same timestamp
    
    # New values
    df_data = {
        'timestamp': [ts],
        'temperature': [30.0], # Changed
        'humidity': [60.0],
        'wind_speed': [5.5],
        'pm10': [15.0],
        'pm25': [7.0],
        'predicted_pm25': [7.2]
    }
    df = pd.DataFrame(df_data)
    
    # Insert again
    load_to_db(db_connection, df, TEST_CITY_NAME, TEST_LAT, TEST_LNG, TEST_COUNTRY_CODE)
    
    # Verify update
    cur = db_connection.cursor()
    cur.execute(
        "SELECT temperature FROM fact_weather WHERE timestamp = %s AND city_id = (SELECT city_id FROM dim_city WHERE name = %s)",
        (ts, TEST_CITY_NAME)
    )
    row = cur.fetchone()
    assert float(row[0]) == 30.0 # Should be updated
    cur.close()
