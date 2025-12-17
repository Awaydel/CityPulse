"""
Скрипт для автоматического запуска всех тестов с генерацией отчетов
Usage: python scripts/run_tests.py
"""
import subprocess
import sys
import os
from datetime import datetime

def run_command(cmd, description):
    """Выполняет команду и выводит результат"""
    print(f"\n{'='*60}")
    print(f">>> {description}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    if result.returncode != 0:
        print(f"❌ FAILED: {description}")
        return False
    else:
        print(f"✅ PASSED: {description}")
        return True

def main():
    """Основная функция запуска тестов"""
    print(f"\n🚀 Запуск тестов качества - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # 1. Unit Tests с покрытием
    results['unit'] = run_command(
        "pytest tests/test_etl.py tests/test_api.py --cov=services --cov=server --cov-report=term --cov-report=html",
        "Unit-тесты (ETL + API) с покрытием"
    )
    
    # 2. Data Quality Tests
    results['dq'] = run_command(
        "pytest tests/test_data_quality.py -v",
        "Тесты качества данных (Data Quality)"
    )
    
    # 3. Integration Tests
    results['integration'] = run_command(
        "pytest tests/test_integration.py -v",
        "Интеграционные тесты (DB roundtrip)"
    )
    
    # 4. E2E Tests
    results['e2e'] = run_command(
        "pytest tests/test_e2e.py -v",
        "End-to-End тесты (полный пайплайн)"
    )
    
    # 5. All tests with full coverage
    results['all'] = run_command(
        "pytest --cov=services --cov=server --cov-report=term --cov-report=html:htmlcov",
        "ВСЕ ТЕСТЫ с полным отчетом о покрытии"
    )
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print(f"{'='*60}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_type, passed_flag in results.items():
        status = "✅ PASS" if passed_flag else "❌ FAIL"
        print(f"{test_type.upper():15} {status}")
    
    print(f"\nИтого: {passed}/{total} категорий тестов прошли успешно")
    
    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("📁 HTML отчет о покрытии: htmlcov/index.html")
        return 0
    else:
        print("\n⚠️ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ!")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
