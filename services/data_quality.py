"""
Data Quality Checker Module
Проверка качества данных: схемы, диапазоны, свежесть, согласованность.
"""
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import os

logger = logging.getLogger(__name__)

class DataQualityChecker:
    """Класс для проверки качества данных"""
    
    def __init__(self):
        self.violations = []
        
    def check_schema(self, df: pd.DataFrame, required_columns: List[str]) -> bool:
        """Проверка наличия обязательных колонок"""
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            violation = {
                'check': 'schema',
                'severity': 'CRITICAL',
                'message': f'Отсутствуют обязательные колонки: {missing}'
            }
            self.violations.append(violation)
            logger.error(violation['message'])
            return False
        return True
    
    def check_null_values(self, df: pd.DataFrame, columns: List[str]) -> bool:
        """Проверка на NULL значения в обязательных полях"""
        has_violations = False
        for col in columns:
            if col in df.columns:
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    total = len(df)
                    null_rate = (null_count / total) * 100
                    violation = {
                        'check': 'null_values',
                        'severity': 'WARNING',
                        'column': col,
                        'null_count': null_count,
                        'null_rate': f'{null_rate:.2f}%',
                        'message': f'Колонка {col} содержит {null_count} NULL значений ({null_rate:.2f}%)'
                    }
                    self.violations.append(violation)
                    logger.warning(violation['message'])
                    has_violations = True
        return not has_violations
    
    def check_ranges(self, df: pd.DataFrame, range_rules: Dict[str, tuple]) -> bool:
        """
        Проверка диапазонов значений
        range_rules: {'column_name': (min_value, max_value)}
        """
        has_violations = False
        for col, (min_val, max_val) in range_rules.items():
            if col in df.columns:
                out_of_range = df[(df[col] < min_val) | (df[col] > max_val)]
                if not out_of_range.empty:
                    violation_count = len(out_of_range)
                    total = len(df)
                    violation_rate = (violation_count / total) * 100
                    
                    violation = {
                        'check': 'range',
                        'severity': 'ERROR',
                        'column': col,
                        'expected_range': f'[{min_val}, {max_val}]',
                        'violation_count': violation_count,
                        'violation_rate': f'{violation_rate:.2f}%',
                        'message': f'Колонка {col}: {violation_count} значений вне диапазона [{min_val}, {max_val}]'
                    }
                    self.violations.append(violation)
                    logger.error(violation['message'])
                    has_violations = True
        return not has_violations
    
    def check_freshness(self, df: pd.DataFrame, timestamp_col: str = 'timestamp', max_age_hours: int = 24) -> bool:
        """Проверка свежести данных (не старее max_age_hours)"""
        if timestamp_col not in df.columns:
            logger.warning(f'Колонка {timestamp_col} не найдена для проверки свежести')
            return True
        
        df[timestamp_col] = pd.to_datetime(df[timestamp_col])
        now = pd.Timestamp.now()
        oldest = df[timestamp_col].min()
        
        age_hours = (now - oldest).total_seconds() / 3600
        
        if age_hours > max_age_hours:
            violation = {
                'check': 'freshness',
                'severity': 'WARNING',
                'oldest_record': str(oldest),
                'age_hours': f'{age_hours:.2f}',
                'max_allowed_hours': max_age_hours,
                'message': f'Данные устарели: самая старая запись {oldest} (возраст {age_hours:.2f} часов)'
            }
            self.violations.append(violation)
            logger.warning(violation['message'])
            return False
        return True
    
    def check_uniqueness(self, df: pd.DataFrame, columns: List[str]) -> bool:
        """Проверка уникальности по набору колонок"""
        duplicates = df[df.duplicated(subset=columns, keep=False)]
        if not duplicates.empty:
            dup_count = len(duplicates)
            violation = {
                'check': 'uniqueness',
                'severity': 'ERROR',
                'columns': columns,
                'duplicate_count': dup_count,
                'message': f'Найдено {dup_count} дубликатов по колонкам {columns}'
            }
            self.violations.append(violation)
            logger.error(violation['message'])
            return False
        return True
    
    def generate_report(self, output_file: str = 'dq_report.csv'):
        """Генерация отчета о нарушениях качества данных"""
        if self.violations:
            df_violations = pd.DataFrame(self.violations)
            df_violations.to_csv(output_file, index=False, encoding='utf-8')
            logger.info(f'Отчет о нарушениях качества данных сохранен в {output_file}')
            return output_file
        else:
            logger.info('Нарушений качества данных не обнаружено')
            return None
    
    def get_quality_score(self) -> float:
        """Расчет общей оценки качества данных (0-100)"""
        if not self.violations:
            return 100.0
        
        # Weighted scoring by severity
        severity_weights = {
            'CRITICAL': 30,
            'ERROR': 20,
            'WARNING': 10
        }
        
        total_penalty = sum(severity_weights.get(v['severity'], 10) for v in self.violations)
        score = max(0, 100 - total_penalty)
        return score


def validate_air_quality_data(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Валидация данных о качестве воздуха
    Возвращает отчет с результатами проверок
    """
    checker = DataQualityChecker()
    
    # 1. Проверка схемы
    required_cols = ['timestamp', 'temperature', 'humidity', 'wind_speed', 'pm10', 'pm25']
    schema_ok = checker.check_schema(df, required_cols)
    
    # 2. Проверка NULL значений в критичных полях
    checker.check_null_values(df, ['timestamp'])
    
    # 3. Проверка диапазонов
    range_rules = {
        'temperature': (-50, 60),  # °C
        'humidity': (0, 100),       # %
        'wind_speed': (0, 200),     # km/h
        'pm10': (0, 500),           # μg/m³
        'pm25': (0, 300)            # μg/m³
    }
    checker.check_ranges(df, range_rules)
    
    # 4. Проверка уникальности (если есть city_name или похожие идентификаторы)
    if 'time' in df.columns:
        checker.check_uniqueness(df, ['time'])
    
    # 5. Генерация отчета
    report_file = checker.generate_report()
    
    # 6. Общая оценка
    quality_score = checker.get_quality_score()
    
    return {
        'passed': len(checker.violations) == 0,
        'quality_score': quality_score,
        'violations_count': len(checker.violations),
        'violations': checker.violations,
        'report_file': report_file
    }
