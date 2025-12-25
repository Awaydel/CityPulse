-- 2. Таблица измерений: Города
CREATE TABLE IF NOT EXISTS dim_city (
    city_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    country_code VARCHAR(5),
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL
);

-- Заполнение справочника городов (стартовые данные)
INSERT INTO dim_city (name, country_code, latitude, longitude) VALUES
('Москва', 'RU', 55.7558, 37.6173),
('Ульяновск', 'RU', 54.3141, 48.4031),
('Лондон', 'GB', 51.5074, -0.1278),
('Берлин', 'DE', 52.5200, 13.4050)
ON CONFLICT DO NOTHING;

-- 3. Таблица фактов: Погода
CREATE TABLE IF NOT EXISTS fact_weather (
    weather_id SERIAL PRIMARY KEY,
    city_id INTEGER REFERENCES dim_city(city_id),
    timestamp TIMESTAMP NOT NULL,
    temperature DECIMAL(5,2),      -- Температура в °C
    humidity DECIMAL(5,2),         -- Влажность в %
    wind_speed DECIMAL(5,2),       -- Скорость ветра в км/ч
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(city_id, timestamp)     -- Защита от дублей
);

-- 4. Таблица фактов: Качество воздуха
CREATE TABLE IF NOT EXISTS fact_air_quality (
    aq_id SERIAL PRIMARY KEY,
    city_id INTEGER REFERENCES dim_city(city_id),
    timestamp TIMESTAMP NOT NULL,
    pm10 DECIMAL(6,2),
    pm25 DECIMAL(6,2),
    predicted_pm25 DECIMAL(6,2),   -- Результат работы ML модели
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(city_id, timestamp)     -- Защита от дублей
);

-- Индексы для ускорения
CREATE INDEX idx_weather_time ON fact_weather(timestamp);
CREATE INDEX idx_aq_time ON fact_air_quality(timestamp);

-- 5. VIEW (Витрина данных): Объединяет таблицы для удобного чтения сервером
CREATE OR REPLACE VIEW dm_dashboard_analytics AS
SELECT 
    c.name as city_name,
    w.timestamp,
    w.temperature,
    w.humidity,
    w.wind_speed,
    aq.pm10,
    aq.pm25,
    aq.predicted_pm25
FROM fact_weather w
JOIN dim_city c ON w.city_id = c.city_id
LEFT JOIN fact_air_quality aq ON w.city_id = aq.city_id AND w.timestamp = aq.timestamp
ORDER BY w.timestamp DESC;

ALTER TABLE dim_city ADD CONSTRAINT dim_city_name_key UNIQUE (name);