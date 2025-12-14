import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ScatterChart, Scatter, ZAxis, ComposedChart, Area
} from 'recharts';
import { UnifiedDataPoint } from '../types';

// --- TRENDS CHART ---

interface TrendsProps {
  data: UnifiedDataPoint[];
  showPrediction?: boolean; // Новый проп для переключателя
}

export const TrendsChart: React.FC<TrendsProps> = ({ data, showPrediction = true }) => {
  return (
    <div className="h-full w-full min-h-[300px]">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorPm" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} vertical={false} />
          
          <XAxis 
            dataKey="displayTime" 
            tick={{ fontSize: 10, fill: '#64748b' }} 
            minTickGap={30}
            stroke="#cbd5e1"
          />
          
          {/* Левая ось: PM2.5 */}
          <YAxis 
            yAxisId="left" 
            label={{ value: 'PM 2.5', angle: -90, position: 'insideLeft', fontSize: 10, fill: '#64748b' }} 
            tick={{ fontSize: 10, fill: '#64748b' }}
            stroke="#cbd5e1"
          />
          
          {/* Правая ось: Температура (для контекста) */}
          <YAxis 
            yAxisId="right" 
            orientation="right" 
            label={{ value: 'Темп. (°C)', angle: 90, position: 'insideRight', fontSize: 10, fill: '#64748b' }} 
            tick={{ fontSize: 10, fill: '#64748b' }}
            stroke="#cbd5e1"
          />
          
          <Tooltip 
            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
            labelStyle={{ color: '#64748b', fontSize: '12px', marginBottom: '5px' }}
            itemStyle={{ fontSize: '12px', padding: 0 }}
          />
          
          <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />

          {/* 1. Основной график (Факт) - Область */}
          <Area 
            yAxisId="left" 
            type="monotone" 
            dataKey="pm25" 
            stroke="#ef4444" 
            fill="url(#colorPm)" 
            name="Факт PM 2.5" 
            strokeWidth={2}
          />

          {/* 2. Линия Погоды (Температура) */}
          <Line 
            yAxisId="right" 
            type="monotone" 
            dataKey="temperature" 
            stroke="#3b82f6" 
            dot={false} 
            strokeWidth={2} 
            name="Температура" 
            opacity={0.5} // Делаем полупрозрачной, чтобы не мешала
          />

          {/* 3. ML Прогноз (Рисуем только если showPrediction = true) */}
          {showPrediction && (
            <Line 
              yAxisId="left" 
              type="monotone" 
              dataKey="predictedPM25" 
              stroke="#8b5cf6" 
              strokeDasharray="5 5" 
              strokeWidth={2} 
              dot={false} 
              name="AI Прогноз" 
            />
          )}

        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

// --- CORRELATION CHART ---

interface CorrelationProps {
  data: UnifiedDataPoint[];
  xKey?: 'temperature' | 'windSpeed' | 'humidity'; // Принимаем ключ для оси X
}

export const CorrelationChart: React.FC<CorrelationProps> = ({ data, xKey = 'temperature' }) => {
  
  // Конфигурация для осей в зависимости от выбранной кнопки
  const config = {
    temperature: { label: 'Температура', unit: '°C', color: '#3b82f6' },
    windSpeed:   { label: 'Ветер', unit: 'км/ч', color: '#06b6d4' },
    humidity:    { label: 'Влажность', unit: '%', color: '#8b5cf6' }
  };
  
  const current = config[xKey];

  // Фильтруем null значения, чтобы график не ломался
  const cleanData = data.filter(d => d.pm25 !== null && d[xKey] !== null);

  return (
    <div className="h-full w-full min-h-[250px]">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          
          {/* Динамическая ось X */}
          <XAxis 
            type="number" 
            dataKey={xKey} 
            name={current.label} 
            unit={current.unit}
            tick={{ fontSize: 10, fill: '#64748b' }}
            label={{ value: `${current.label} (${current.unit})`, position: 'bottom', offset: 0, fontSize: 11, fill: '#64748b' }}
            domain={['auto', 'auto']}
          />
          
          <YAxis 
            type="number" 
            dataKey="pm25" 
            name="PM 2.5" 
            unit=" мкг/м³" 
            tick={{ fontSize: 10, fill: '#64748b' }}
            label={{ value: 'PM 2.5', angle: -90, position: 'insideLeft', fontSize: 11, fill: '#64748b' }} 
          />
          
          <Tooltip 
            cursor={{ strokeDasharray: '3 3' }} 
            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
          />
          
          <Scatter 
            name="Корреляция" 
            data={cleanData} 
            fill={current.color} 
            fillOpacity={0.6} 
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
};

// --- RISK HEATMAP ---

interface HeatmapProps {
  data: UnifiedDataPoint[];
}

export const RiskHeatmap: React.FC<HeatmapProps> = ({ data }) => {
  // Цветовая логика
  const getRiskClass = (pm25: number | null) => {
    if (pm25 === null) return 'bg-slate-100 text-slate-300';
    if (pm25 < 12) return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    if (pm25 < 35.5) return 'bg-yellow-100 text-yellow-700 border-yellow-200';
    if (pm25 < 55.5) return 'bg-orange-100 text-orange-700 border-orange-200';
    return 'bg-red-100 text-red-700 border-red-200';
  };

  // Берем последние 48 часов для карты
  const recentData = [...data].reverse().slice(0, 48);

  return (
    <div className="w-full h-full overflow-y-auto pr-2">
      <div className="grid grid-cols-6 sm:grid-cols-8 md:grid-cols-12 gap-2">
        {recentData.map((d, idx) => {
           // Форматируем время для тултипа и отображения
           const date = new Date(d.timestamp);
           const hour = date.getHours();
           const day = date.toLocaleDateString('ru-RU', { weekday: 'short' });

           return (
            <div 
              key={idx} 
              className={`flex flex-col items-center justify-center h-12 rounded border ${getRiskClass(d.pm25)} transition-transform hover:scale-105 cursor-help`}
              title={`${day}, ${d.displayTime}\nPM2.5: ${d.pm25}\nТемп: ${d.temperature}`}
            >
              <span className="text-[10px] font-mono font-bold opacity-80">{hour}:00</span>
              <span className="font-bold text-xs">{d.pm25 ? Math.round(d.pm25) : '-'}</span>
            </div>
           )
        })}
        {recentData.length === 0 && <div className="col-span-full text-center text-slate-400 py-10">Нет данных</div>}
      </div>
      
      {/* Легенда */}
      <div className="flex gap-4 mt-4 text-[10px] text-slate-500 justify-end flex-wrap border-t border-slate-100 pt-2">
        <div className="flex items-center gap-1"><div className="w-2 h-2 bg-emerald-400 rounded-full"></div> Отлично</div>
        <div className="flex items-center gap-1"><div className="w-2 h-2 bg-yellow-400 rounded-full"></div> Норма</div>
        <div className="flex items-center gap-1"><div className="w-2 h-2 bg-orange-400 rounded-full"></div> Вредно</div>
        <div className="flex items-center gap-1"><div className="w-2 h-2 bg-red-500 rounded-full"></div> Опасно</div>
      </div>
    </div>
  );
};