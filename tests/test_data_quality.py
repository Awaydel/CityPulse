import pytest
import pandas as pd
import sys
import os

# Explicitly add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.data_quality import DataQualityChecker, validate_air_quality_data

def test_check_schema_success():
    """Тест успешной проверки схемы"""
    df = pd.DataFrame({
        'col1': [1, 2, 3],
        'col2': [4, 5, 6]
    })
    
    checker = DataQualityChecker()
    result = checker.check_schema(df, ['col1', 'col2'])
    assert result is True
    assert len(checker.violations) == 0

def test_check_schema_fail():
    """Тест неуспешной проверки схемы (отсутствуют колонки)"""
    df = pd.DataFrame({
        'col1': [1, 2, 3]
    })
    
    checker = DataQualityChecker()
    result = checker.check_schema(df, ['col1', 'col2', 'col3'])
    assert result is False
    assert len(checker.violations) == 1
    assert checker.violations[0]['severity'] == 'CRITICAL'

def test_check_null_values():
    """Тест проверки NULL значений"""
    df = pd.DataFrame({
        'col1': [1, 2, None],
        'col2': [4, None, 6]
    })
    
    checker = DataQualityChecker()
    result = checker.check_null_values(df, ['col1', 'col2'])
    assert result is False
    assert len(checker.violations) == 2  # Both columns have NULLs

def test_check_ranges_success():
    """Тест успешной проверки диапазонов"""
    df = pd.DataFrame({
        'temperature': [10, 20, 30],
        'pm25': [5, 10, 15]
    })
    
    checker = DataQualityChecker()
    range_rules = {
        'temperature': (0, 40),
        'pm25': (0, 50)
    }
    result = checker.check_ranges(df, range_rules)
    assert result is True
    assert len(checker.violations) == 0

def test_check_ranges_fail():
    """Тест неуспешной проверки диапазонов"""
    df = pd.DataFrame({
        'temperature': [-100, 20, 150],  # Out of range
        'pm25': [5, 10, -5]  # Negative value
    })
    
    checker = DataQualityChecker()
    range_rules = {
        'temperature': (-50, 60),
        'pm25': (0, 300)
    }
    result = checker.check_ranges(df, range_rules)
    assert result is False
    assert len(checker.violations) == 2  # Both columns have violations

def test_check_uniqueness_success():
    """Тест успешной проверки уникальности"""
    df = pd.DataFrame({
        'id': [1, 2, 3],
        'value': [10, 20, 30]
    })
    
    checker = DataQualityChecker()
    result = checker.check_uniqueness(df, ['id'])
    assert result is True
    assert len(checker.violations) == 0

def test_check_uniqueness_fail():
    """Тест неуспешной проверки уникальности (есть дубликаты)"""
    df = pd.DataFrame({
        'id': [1, 2, 2, 3],
        'value': [10, 20, 20, 30]
    })
    
    checker = DataQualityChecker()
    result = checker.check_uniqueness(df, ['id', 'value'])
    assert result is False
    assert len(checker.violations) == 1

def test_quality_score():
    """Тест расчета оценки качества"""
    checker = DataQualityChecker()
    
    # No violations = 100
    assert checker.get_quality_score() == 100.0
    
    # Add some violations
    checker.violations.append({'severity': 'WARNING'})
    checker.violations.append({'severity': 'ERROR'})
    
    score = checker.get_quality_score()
    assert score < 100.0
    assert score >= 0.0

def test_validate_air_quality_data():
    """Интеграционный тест валидации воздушных данных"""
    df = pd.DataFrame({
        'timestamp': pd.date_range('2025-01-01', periods=3, freq='h'),
        'temperature': [20, 21, 19],
        'humidity': [50, 55, 60],
        'wind_speed': [3.5, 4.0, 3.0],
        'pm10': [12, 13, 15],
        'pm25': [5, 6, 7]
    })
    
    result = validate_air_quality_data(df)
    
    assert 'passed' in result
    assert 'quality_score' in result
    assert 'violations_count' in result
    assert result['quality_score'] >= 0

def test_validate_air_quality_data_with_violations():
    """Тест валидации с нарушениями"""
    df = pd.DataFrame({
        'timestamp': pd.date_range('2025-01-01', periods=3, freq='h'),
        'temperature': [-100, 21, 19],  # Out of range
        'humidity': [50, 150, 60],  # Out of range
        'wind_speed': [3.5, 4.0, 3.0],
        'pm10': [12, 13, 15],
        'pm25': [5, 6, 7]
    })
    
    result = validate_air_quality_data(df)
    
    assert result['passed'] is False
    assert result['violations_count'] > 0
    assert result['quality_score'] < 100
