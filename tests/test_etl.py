import sys
import os

# Explicitly add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from services.etl import fetch_open_meteo_data, transform_data, train_and_predict_ml

# --- Тесты для API Клиента (fetch_open_meteo_data) ---

@patch('services.etl.requests.get')
def test_fetch_open_meteo_data(mock_get):
    """
    Тест функции получения данных API.
    Проверяет, что запросы отправляются и возвращаются корректные JSON данные.
    """
    # Подготовка моков
    mock_response_weather = MagicMock()
    mock_response_weather.json.return_value = {'weather': 'data'}
    
    mock_response_aq = MagicMock()
    mock_response_aq.json.return_value = {'air_quality': 'data'}
    
    # Настраиваем side_effect для возврата разных ответов на последовательные вызовы
    mock_get.side_effect = [mock_response_weather, mock_response_aq]

    # Вызов функции
    w_res, aq_res = fetch_open_meteo_data(55.75, 37.61)

    # Проверки
    assert w_res == {'weather': 'data'}
    assert aq_res == {'air_quality': 'data'}
    assert mock_get.call_count == 2 # Должно быть два запроса

# --- Тесты для Унификации и Парсинга (transform_data) ---

def test_transform_data_success():
    """
    Тест успешной трансформации и объединения данных.
    Проверяет создание DataFrame, объединение по времени и очистку данных.
    """
    # Подготовка тестовых данных
    w_data = {
        'hourly': {
            'time': ['2023-01-01T00:00', '2023-01-01T01:00', '2023-01-01T02:00'],
            'temperature_2m': [20.0, 21.0, 19.5],
            'relative_humidity_2m': [50, 55, 60],
            'wind_speed_10m': [3.5, 4.0, 3.0]
        }
    }
    
    aq_data = {
        'hourly': {
            'time': ['2023-01-01T00:00', '2023-01-01T01:00', '2023-01-01T02:00'],
            'pm10': [12.0, -5.0, 15.0], # -5.0 это аномалия
            'pm2_5': [5.0, 6.0, -1.0]   # -1.0 это аномалия
        }
    }

    # Вызов функции
    df = transform_data(w_data, aq_data)

    # Проверки
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert 'timestamp' in df.columns
    
    # Проверка объединения
    assert list(df['temperature']) == [20.0, 21.0, 19.5]
    
    # Проверка очистки аномалий (отрицательные значения должны стать NaN)
    assert pd.isna(df.loc[1, 'pm10']) # -5.0 -> NaN
    assert df.loc[0, 'pm10'] == 12.0
    
    assert pd.isna(df.loc[2, 'pm25']) # -1.0 -> NaN
    assert df.loc[0, 'pm25'] == 5.0

def test_transform_data_mismatch_length():
    """
    Тест на случай, если данные имеют разную длину (inner join должен отработать).
    В данном случае inner join оставит только пересекающиеся по времени записи.
    """
    w_data = {
        'hourly': {
            'time': ['2023-01-01T00:00', '2023-01-01T01:00'],
            'temperature_2m': [20.0, 21.0],
            'relative_humidity_2m': [50, 55],
            'wind_speed_10m': [3.5, 4.0]
        }
    }
    
    aq_data = {
        'hourly': {
            'time': ['2023-01-01T00:00'], # Только одна запись
            'pm10': [10.0],
            'pm2_5': [5.0]
        }
    }
    
    df = transform_data(w_data, aq_data)
    
    assert len(df) == 1
    assert df.iloc[0]['time'] == '2023-01-01T00:00'

# --- Тесты для ML Логики (train_and_predict_ml) ---

def test_train_and_predict_ml_success():
    """
    Тест успешного обучения ML модели.
    Проверяет, что колонка predicted_pm25 добавляется и заполняется.
    """
    # Создаем DataFrame с "хорошими" данными (> 10 строк)
    data = {
        'temperature': np.random.rand(20) * 30,
        'wind_speed': np.random.rand(20) * 10,
        'humidity': np.random.rand(20) * 100,
        'pm25': np.random.rand(20) * 50
    }
    df = pd.DataFrame(data)
    
    # Вызов функции
    df_result = train_and_predict_ml(df)
    
    # Проверки
    assert 'predicted_pm25' in df_result.columns
    assert not df_result['predicted_pm25'].isna().all() # Не все значения NaN
    
def test_train_and_predict_ml_not_enough_data():
    """
    Тест поведения при недостаточном количестве данных (< 10 строк).
    Модель не должна обучаться, колонка predicted_pm25 должна быть None.
    """
    # Данные меньше 10 строк
    data = {
        'temperature': [20.0],
        'wind_speed': [5.0],
        'humidity': [50.0],
        'pm25': [10.0]
    }
    df = pd.DataFrame(data)
    
    # Вызов функции
    df_result = train_and_predict_ml(df)
    
    # Проверки
    assert 'predicted_pm25' in df_result.columns
    assert df_result['predicted_pm25'].isna().all() # Все значения должны быть None/NaN

# --- Тесты для DB и Main (Mocked) ---

from services.etl import get_db_connection, load_to_db, main

@patch('services.etl.psycopg2.connect')
def test_get_db_connection_success(mock_connect):
    """Тест успешного подключения к БД"""
    mock_connect.return_value = 'connection_obj'
    conn = get_db_connection()
    assert conn == 'connection_obj'

@patch('services.etl.psycopg2.connect')
def test_get_db_connection_fail(mock_connect):
    """Тест неуспешного подключения"""
    mock_connect.side_effect = Exception("Connection error")
    conn = get_db_connection()
    assert conn is None

@patch('services.etl.execute_values')
def test_load_to_db(mock_execute_values):
    """Тест функции загрузки в БД (mocking SQL execution)"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    
    # Mocking fetchone logic for city_id
    # First call: insert city -> returns city_id
    mock_cursor.fetchone.return_value = [1] 
    
    # Data for test
    df_data = {
        'timestamp': [pd.Timestamp('2023-01-01')],
        'temperature': [20.0],
        'humidity': [50.0],
        'wind_speed': [5.0],
        'pm10': [10.0],
        'pm25': [5.0],
        'predicted_pm25': [5.5]
    }
    df = pd.DataFrame(df_data)
    
    load_to_db(mock_conn, df, "TestCity", 55.0, 37.0, "RU")
    
    # Verify calls
    assert mock_cursor.execute.call_count >= 1 # At least inserts city
    
    # Verify execute_values was called twice (weather and aq)
    assert mock_execute_values.call_count == 2
    
    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()

@patch('services.etl.get_db_connection')
@patch('services.etl.fetch_open_meteo_data')
@patch('services.etl.transform_data')
@patch('services.etl.train_and_predict_ml')
@patch('services.etl.load_to_db')
def test_main_success(mock_load, mock_train, mock_transform, mock_fetch, mock_get_db):
    """Тест основной функции main (full happy path)"""
    mock_get_db.return_value = MagicMock()
    
    # Setup mock returns
    mock_fetch.return_value = ({}, {})
    mock_transform.return_value = pd.DataFrame()
    mock_train.return_value = pd.DataFrame()
    
    main()
    
    assert mock_fetch.call_count == 4 # 4 cities in config
    assert mock_load.call_count == 4
    mock_get_db.return_value.close.assert_called_once()

@patch('services.etl.get_db_connection')
def test_main_no_db(mock_get_db):
    """Тест main если нет подключения к БД"""
    mock_get_db.return_value = None
    main()
    # Should just return
    mock_get_db.assert_called_once()

