// Этот файл заменяет старый api.ts.
// Теперь мы не ходим в Open-Meteo, а ходим на свой бэкенд.

import { UnifiedDataPoint } from '../types';

const BACKEND_URL = 'http://localhost:8000/api';

export interface City {
  name: string;
  lat: number;
  lng: number;
  country: string;
}

export const fetchCities = async (): Promise<City[]> => {
  const response = await fetch(`${BACKEND_URL}/cities`);
  if (!response.ok) throw new Error('Ошибка загрузки городов с сервера');
  const data = await response.json();
  // Маппинг формата БД в формат фронтенда
  return data.cities.map((c: any) => ({
    name: c.name,
    lat: c.latitude,
    lng: c.longitude,
    country: c.country_code
  }));
};

export const fetchDashboardData = async (cityName: string): Promise<UnifiedDataPoint[]> => {
  const response = await fetch(`${BACKEND_URL}/measurements?city_name=${encodeURIComponent(cityName)}`);
  
  if (!response.ok) {
    throw new Error(`Ошибка сервера: ${response.statusText}`);
  }
  
  const json = await response.json();
  
  // Трансформация данных для графика
  return json.data.map((row: any) => ({
    timestamp: row.timestamp,
    displayTime: new Date(row.timestamp).toLocaleDateString('ru-RU', {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
    }),
    pm10: row.pm10,
    pm25: row.pm25,
    temperature: row.temperature,
    windSpeed: row.wind_speed,
    humidity: row.humidity,
    predictedPM25: row.predicted_pm25
  }));
};
