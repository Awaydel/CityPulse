import pytest
import psycopg2
from fastapi.testclient import TestClient
from datetime import datetime
from unittest.mock import patch, MagicMock
import sys
import os

# Explicitly add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server import app
from services.etl import DB_CONFIG, transform_data, train_and_predict_ml, load_to_db

client = TestClient(app)

# --- Test Config ---
E2E_CITY_NAME = "E2ETestCity"
E2E_COUNTRY_CODE = "E2E"
E2E_LAT = 45.0
E2E_LNG = 50.0

# Check if DB is available
def is_db_available():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.close()
        return True
    except:
        return False

@pytest.fixture(scope="module")
def e2e_db_connection():
    """Создает подключение к БД для E2E теста"""
    conn = psycopg2.connect(**DB_CONFIG)
    yield conn
    
    # Cleanup after tests
    cur = conn.cursor()
    cur.execute("DELETE FROM fact_weather WHERE city_id IN (SELECT city_id FROM dim_city WHERE name = %s)", (E2E_CITY_NAME,))
    cur.execute("DELETE FROM fact_air_quality WHERE city_id IN (SELECT city_id FROM dim_city WHERE name = %s)", (E2E_CITY_NAME,))
    cur.execute("DELETE FROM dim_city WHERE name = %s", (E2E_CITY_NAME,))
    conn.commit()
    cur.close()
    conn.close()

@pytest.mark.skipif(
    not is_db_available(),
    reason="PostgreSQL not available (expected in CI)"
)

def test_e2e_etl_to_api(e2e_db_connection):
    """
    E2E Тест: полный цикл от ETL до API
    1. Подготовка тестовых данных (имитация API response)
    2. Запуск ETL процесса (transform + ML + load)
    3. Вызов API для получения данных
    4. Проверка корректности данных
    """
    
    # 1. Prepare Mock Data (simulating API response from Open-Meteo)
    w_data = {
        'hourly': {
            'time': ['2025-01-01T00:00', '2025-01-01T01:00', '2025-01-01T02:00'],
            'temperature_2m': [20.0, 21.0, 19.5],
            'relative_humidity_2m': [50, 55, 60],
            'wind_speed_10m': [3.5, 4.0, 3.0]
        }
    }
    
    aq_data = {
        'hourly': {
            'time': ['2025-01-01T00:00', '2025-01-01T01:00', '2025-01-01T02:00'],
            'pm10': [12.0, 13.0, 15.0],
            'pm2_5': [5.0, 6.0, 7.0]
        }
    }
    
    # 2. Run ETL Pipeline (Transform + ML + Load)
    df = transform_data(w_data, aq_data)
    assert len(df) == 3
    
    df = train_and_predict_ml(df)
    assert 'predicted_pm25' in df.columns
    
    load_to_db(e2e_db_connection, df, E2E_CITY_NAME, E2E_LAT, E2E_LNG, E2E_COUNTRY_CODE)
    
    # 3. Call API to fetch data
    response = client.get(f"/api/measurements?city_name={E2E_CITY_NAME}")
    
    # 4. Verify API Response
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 3
    
    # Verify first record
    first_record = data["data"][0]
    assert first_record["city_name"] == E2E_CITY_NAME
    assert first_record["temperature"] is not None
    assert first_record["pm25"] is not None
    assert first_record["predicted_pm25"] is not None
    
    # Verify data consistency (values should match what we loaded)
    temps = [r["temperature"] for r in data["data"]]
    assert 20.0 in temps or 21.0 in temps or 19.5 in temps  # At least one of our temps is present

@patch('server.get_db_connection')
def test_e2e_api_no_data(mock_db):
    """
    E2E тест: проверка поведения API когда данных нет
    """
    # Mock DB connection
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []  # No data
    mock_db.return_value = mock_conn
    
    response = client.get("/api/measurements?city_name=NonExistentCity123456")
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
    assert "message" in data
    assert "не найдены" in data["message"]
