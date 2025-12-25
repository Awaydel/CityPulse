export interface City {
  name: string;
  lat: number;
  lng: number;
  country: string;
}

// Data point after ETL process
export interface UnifiedDataPoint {
  timestamp: string; // ISO String
  displayTime: string; // Formatted for charts
  pm10: number | null;
  pm25: number | null;
  temperature: number | null;
  windSpeed: number | null;
  humidity: number | null;
  predictedPM25: number | null; // ML Prediction
}

export interface MLStats {
  rSquared: number;
  mse: number;
  weights: {
    temperature: number;
    windSpeed: number;
    humidity: number;
  };
}

export interface DataQualityReport {
  totalRows: number;
  missingPM25: number;
  missingTemp: number;
  anomalies: number; // e.g. negative values
  qualityScore: number; // 0-100
  mlStats?: MLStats;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'info' | 'success' | 'warning' | 'error';
  message: string;
}

// Open-Meteo Weather API Response
export interface OpenMeteoWeatherResponse {
  hourly: {
    time: string[];
    temperature_2m: (number | null)[];
    relative_humidity_2m: (number | null)[];
    wind_speed_10m: (number | null)[];
  };
}

// Open-Meteo Air Quality API Response
export interface OpenMeteoAQResponse {
  hourly: {
    time: string[];
    pm10: (number | null)[];
    pm2_5: (number | null)[];
  };
}
