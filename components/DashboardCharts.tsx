import React, { useMemo } from 'react';
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ScatterChart, Scatter, ZAxis, Cell
} from 'recharts';
import { UnifiedDataPoint } from '../types';

// --- HELPERS ---

// Расчет корреляции Пирсона
function calculatePearsonCorrelation(x: number[], y: number[]) {
  const n = x.length;
  if (n === 0) return 0;
  const sumX = x.reduce((a, b) => a + b, 0);
  const sumY = y.reduce((a, b) => a + b, 0);
  const sumXY = x.reduce((sum, xi, i) => sum + xi * y[i], 0);
  const sumX2 = x.reduce((sum, xi) => sum + xi * xi, 0);
  const sumY2 = y.reduce((sum, yi) => sum + yi * yi, 0);

  const numerator = (n * sumXY) - (sumX * sumY);
  const denominator = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));

  return denominator === 0 ? 0 : numerator / denominator;
}

// --- 1. TRENDS CHART (Enhanced with PM10, Rolling Avg, WHO threshold) ---
interface TrendsProps {
  data: UnifiedDataPoint[];
  showPrediction?: boolean;
  chartMode?: 'simple' | 'detailed' | 'weather';
}

// Функция для расчёта скользящего среднего
function calculateRollingAverage(data: UnifiedDataPoint[], window: number = 6): (number | null)[] {
  return data.map((_, idx) => {
    const start = Math.max(0, idx - window + 1);
    const slice = data.slice(start, idx + 1);
    const validValues = slice.filter(d => d.pm25 !== null).map(d => d.pm25!);
    if (validValues.length === 0) return null;
    return validValues.reduce((a, b) => a + b, 0) / validValues.length;
  });
}

export const TrendsChart: React.FC<TrendsProps> = ({ data, showPrediction = true, chartMode = 'simple' }) => {
  const chartData = useMemo(() => {
    const rollingAvg = calculateRollingAverage(data, 6);
    return data.map((d, i) => ({
      ...d,
      rollingAvgPM25: rollingAvg[i] ? Number(rollingAvg[i]!.toFixed(2)) : null
    }));
  }, [data]);

  const WHO_THRESHOLD = 15;

  return (
    <div className="h-full w-full min-h-[300px]">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorPm25" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorPm10" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} vertical={false} />
          <XAxis dataKey="displayTime" tick={{ fontSize: 10 }} minTickGap={30} stroke="#cbd5e1" />
          <YAxis yAxisId="left" label={{ value: 'PM (мкг/м³)', angle: -90, position: 'insideLeft', fontSize: 10 }} tick={{ fontSize: 10 }} stroke="#cbd5e1" />
          {chartMode === 'weather' && (
            <YAxis yAxisId="right" orientation="right" label={{ value: '°C', angle: 90, position: 'insideRight', fontSize: 10 }} tick={{ fontSize: 10 }} stroke="#cbd5e1" />
          )}
          <Tooltip contentStyle={{ borderRadius: '8px' }} labelStyle={{ color: '#64748b' }} />
          <Legend wrapperStyle={{ fontSize: '11px' }} />

          {/* WHO Threshold - always visible */}
          <Line yAxisId="left" type="monotone" dataKey={() => WHO_THRESHOLD} stroke="#dc2626" strokeDasharray="8 4" strokeWidth={1} dot={false} name="ВОЗ" legendType="none" />

          {/* PM2.5 - always visible */}
          <Area yAxisId="left" type="monotone" dataKey="pm25" stroke="#ef4444" fill="url(#colorPm25)" name="PM2.5" strokeWidth={2} />

          {/* Rolling Average - simple & detailed modes */}
          {(chartMode === 'simple' || chartMode === 'detailed') && (
            <Line yAxisId="left" type="monotone" dataKey="rollingAvgPM25" stroke="#10b981" strokeWidth={2} dot={false} name="Сред.6ч" />
          )}

          {/* PM10 - detailed mode only */}
          {chartMode === 'detailed' && (
            <Area yAxisId="left" type="monotone" dataKey="pm10" stroke="#f59e0b" fill="url(#colorPm10)" name="PM10" strokeWidth={1} opacity={0.6} />
          )}

          {/* Temperature - weather mode only */}
          {chartMode === 'weather' && (
            <Line yAxisId="right" type="monotone" dataKey="temperature" stroke="#3b82f6" dot={false} strokeWidth={2} name="Темп" />
          )}

          {/* AI Prediction */}
          {showPrediction && (
            <Line yAxisId="left" type="monotone" dataKey="predictedPM25" stroke="#8b5cf6" strokeDasharray="5 5" strokeWidth={2} dot={false} name="AI" />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

// --- 2. TRUE CORRELATION MATRIX (Требование QA) ---
interface CorrelationProps {
  data: UnifiedDataPoint[];
}

export const CorrelationMatrix: React.FC<CorrelationProps> = ({ data }) => {
  const matrix = useMemo(() => {
    // Подготовка массивов (фильтруем null)
    const validData = data.filter(d =>
      d.pm25 !== null && d.temperature !== null && d.windSpeed !== null && d.humidity !== null
    );

    const pm = validData.map(d => d.pm25!);
    const temp = validData.map(d => d.temperature!);
    const wind = validData.map(d => d.windSpeed!);
    const hum = validData.map(d => d.humidity!);

    const factors = [
      { key: 'pm25', label: 'PM 2.5', values: pm },
      { key: 'temp', label: 'Темп', values: temp },
      { key: 'wind', label: 'Ветер', values: wind },
      { key: 'hum', label: 'Влажн', values: hum },
    ];

    const result = [];
    for (let i = 0; i < factors.length; i++) {
      for (let j = 0; j < factors.length; j++) {
        const corr = calculatePearsonCorrelation(factors[i].values, factors[j].values);
        result.push({
          x: factors[i].label,
          y: factors[j].label,
          value: corr
        });
      }
    }
    return result;
  }, [data]);

  return (
    <div className="w-full h-full flex flex-col items-center justify-center p-2">
      <div className="grid grid-cols-5 gap-1 text-xs">
        {/* Header Row */}
        <div className="col-span-1"></div>
        {['PM 2.5', 'Темп', 'Ветер', 'Влажн'].map(h => (
          <div key={h} className="font-bold text-slate-500 text-center">{h}</div>
        ))}

        {/* Matrix Rows */}
        {['PM 2.5', 'Темп', 'Ветер', 'Влажн'].map((rowLabel) => (
          <React.Fragment key={rowLabel}>
            <div className="font-bold text-slate-500 flex items-center justify-end pr-2">{rowLabel}</div>
            {['PM 2.5', 'Темп', 'Ветер', 'Влажн'].map((colLabel) => {
              const cell = matrix.find(m => m.y === rowLabel && m.x === colLabel);
              const val = cell ? cell.value : 0;
              // Color scale: Blue (-1) -> White (0) -> Red (1)
              const bg = val > 0
                ? `rgba(239, 68, 68, ${Math.abs(val)})` // Red
                : `rgba(59, 130, 246, ${Math.abs(val)})`; // Blue

              return (
                <div
                  key={`${rowLabel}-${colLabel}`}
                  className="w-12 h-12 flex items-center justify-center rounded text-slate-800 font-mono text-[10px] border border-slate-100"
                  style={{ backgroundColor: rowLabel === colLabel ? '#f1f5f9' : bg }}
                  title={`${rowLabel} vs ${colLabel}: ${val.toFixed(3)}`}
                >
                  {rowLabel === colLabel ? '1.0' : val.toFixed(2)}
                </div>
              );
            })}
          </React.Fragment>
        ))}
      </div>
      <div className="mt-4 text-[10px] text-slate-400 text-center w-full">
        <span className="text-blue-500 font-bold">-1 (Обр)</span> ← 0 → <span className="text-red-500 font-bold">+1 (Прям)</span>
      </div>
    </div>
  );
};

// --- 3. TRUE HEATMAP (Day x Hour) (Требование QA) ---
interface HeatmapProps {
  data: UnifiedDataPoint[];
}

export const TrueHeatmap: React.FC<HeatmapProps> = ({ data }) => {
  // Агрегация данных: [День недели][Час] -> Среднее PM2.5
  const grid = useMemo(() => {
    const days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    const hours = Array.from({ length: 24 }, (_, i) => i);

    // Инициализация сетки
    const map = new Map<string, { sum: number, count: number }>();

    data.forEach(d => {
      if (d.pm25 === null) return;
      const date = new Date(d.timestamp);
      // getDay() возвращает 0 (Вс) - 6 (Сб). Конвертируем в наш порядок (Пн-Вс)
      let dayIdx = date.getDay() - 1;
      if (dayIdx === -1) dayIdx = 6;

      const hour = date.getHours();
      const key = `${dayIdx}-${hour}`;

      if (!map.has(key)) map.set(key, { sum: 0, count: 0 });
      const entry = map.get(key)!;
      entry.sum += d.pm25;
      entry.count += 1;
    });

    return days.map((dayName, dIdx) => {
      return hours.map((h) => {
        const key = `${dIdx}-${h}`;
        const entry = map.get(key);
        const avg = entry ? entry.sum / entry.count : null;
        return { day: dayName, hour: h, value: avg };
      });
    });
  }, [data]);

  return (
    <div className="w-full h-full overflow-x-auto">
      <div className="min-w-[500px] h-full flex flex-col">
        {/* Hours Header */}
        <div className="flex mb-1 ml-8">
          {Array.from({ length: 24 }, (_, i) => (
            <div key={i} className="flex-1 text-[9px] text-center text-slate-400 border-l border-transparent hover:border-slate-300">
              {i % 3 === 0 ? i : ''}
            </div>
          ))}
        </div>

        {/* Rows */}
        {grid.map((row, i) => (
          <div key={i} className="flex flex-1 items-center mb-1">
            <div className="w-8 text-[10px] font-bold text-slate-500 text-right pr-2">{row[0].day}</div>
            {row.map((cell) => {
              let bg = 'bg-slate-100'; // No data
              if (cell.value !== null) {
                if (cell.value <= 10) bg = 'bg-emerald-200';
                else if (cell.value <= 20) bg = 'bg-emerald-400';
                else if (cell.value <= 35) bg = 'bg-yellow-400';
                else if (cell.value <= 55) bg = 'bg-orange-500';
                else bg = 'bg-red-600';
              }
              return (
                <div
                  key={cell.hour}
                  className={`flex-1 h-full mx-[1px] rounded-sm ${bg} hover:opacity-80 transition-opacity cursor-pointer`}
                  title={`${cell.day} ${cell.hour}:00, Ср. PM2.5: ${cell.value?.toFixed(1) ?? 'N/A'}`}
                />
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
};