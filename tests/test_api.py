import sys
import os
from datetime import datetime

# Explicitly add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from server import app

client = TestClient(app)

# --- CONFIG ---
@pytest.fixture
def mock_db_conn():
    with patch('server.get_db_connection') as mock:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        mock.return_value = conn
        yield mock, conn, cursor

def test_read_root():
    """Test health check endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "EcoSense API is running", "version": "2.1.0"}

def test_get_cities_success(mock_db_conn):
    """Test getting list of cities"""
    _, _, cursor = mock_db_conn
    
    # Mock return data
    mock_cities = [
        {'city_id': 1, 'name': 'Moscow', 'country_code': 'RU', 'latitude': 55.75, 'longitude': 37.61},
        {'city_id': 2, 'name': 'London', 'country_code': 'GB', 'latitude': 51.50, 'longitude': -0.12}
    ]
    cursor.fetchall.return_value = mock_cities

    response = client.get("/api/cities")
    
    assert response.status_code == 200
    data = response.json()
    assert "cities" in data
    assert len(data["cities"]) == 2
    assert data["cities"][0]["name"] == "Moscow"

def test_get_cities_db_error(mock_db_conn):
    """Test behavior when DB connection fails"""
    mock_get_db, _, _ = mock_db_conn
    mock_get_db.side_effect = Exception("DB Connection Failed")

    response = client.get("/api/cities")
    assert response.status_code == 500
    assert "DB Connection Failed" in response.json()["detail"]

def test_get_measurements_success(mock_db_conn):
    """Test valid measurement request"""
    _, _, cursor = mock_db_conn
    
    mock_data = [
        {
            'city_name': 'Moscow',
            'timestamp': '2023-10-10T12:00:00',
            'temperature': 15.5,
            'humidity': 60,
            'wind_speed': 5.0,
            'pm10': 12.0,
            'pm25': 5.0,
            'predicted_pm25': 5.2
        }
    ]
    cursor.fetchall.return_value = mock_data

    response = client.get("/api/measurements?city_name=Moscow")
    
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 1
    assert data["data"][0]["city_name"] == "Moscow"
    # Pydantic usually handles datetime serialization to string in JSON

def test_get_measurements_no_data(mock_db_conn):
    """Test city with no data"""
    _, _, cursor = mock_db_conn
    cursor.fetchall.return_value = [] # Empty list

    response = client.get("/api/measurements?city_name=UnknownCity")
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
    assert "message" in data
    assert "не найдены" in data["message"]

def test_get_measurements_missing_param():
    """Test validation error for missing parameter"""
    response = client.get("/api/measurements")
    assert response.status_code == 422 # Validation Error
