-- Таблица dim_city
CREATE TABLE dim_city (
    dim_city_pk SERIAL PRIMARY KEY,
    city_name VARCHAR(100) UNIQUE NOT NULL,
    country_name VARCHAR(100),
    timezone_name VARCHAR(50)
);

-- Таблица dim_metric
CREATE TABLE dim_metric (
    dim_metric_pk SERIAL PRIMARY KEY,
    metric_name VARCHAR(50) UNIQUE NOT NULL,
    unit_of_measure VARCHAR(10),
    who_limit_ugm3 NUMERIC
);

-- Таблица фактов: fact_air_quality
CREATE TABLE fact_air_quality (
    fact_aq_pk BIGSERIAL PRIMARY KEY,
    dim_city_fk INTEGER REFERENCES dim_city(dim_city_pk) ON DELETE RESTRICT,
    dim_metric_fk INTEGER REFERENCES dim_metric(dim_metric_pk) ON DELETE RESTRICT,
    timestamp_utc TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    value NUMERIC NOT NULL,
    station_count INTEGER,
    UNIQUE (dim_city_fk, dim_metric_fk, timestamp_utc)
);

-- Таблица фактов: fact_weather
CREATE TABLE fact_weather (
    fact_weather_pk BIGSERIAL PRIMARY KEY,
    dim_city_fk INTEGER REFERENCES dim_city(dim_city_pk) ON DELETE RESTRICT,
    timestamp_utc TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    temperature_c NUMERIC,
    wind_speed_ms NUMERIC
); 
