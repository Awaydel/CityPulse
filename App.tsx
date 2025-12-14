import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { 
  LayoutDashboard, 
  Table as TableIcon, 
  ScrollText, 
  Activity, 
  Wind, 
  Database, 
  BrainCircuit, 
  MapPin, 
  RefreshCw, 
  AlertTriangle, 
  CheckCircle2, 
  Terminal,
  Server,
  Thermometer,
  Droplets,
  ShieldCheck,
  Clock,
  Wifi
} from 'lucide-react';
import { fetchDashboardData, fetchCities, City } from './services/api';
import { UnifiedDataPoint } from './types';
import { TrendsChart, CorrelationChart, RiskHeatmap } from './components/DashboardCharts';

// --- T Y P E S   &   H E L P E R S ---

interface LogEntry {
  id: string;
  time: string;
  type: 'info' | 'success' | 'error';
  message: string;
}

// Оценка качества воздуха (Семантическая унификация)
const getAirQualityStatus = (pm25: number | null) => {
  if (pm25 === null) return { label: 'Нет данных', color: 'bg-slate-100 text-slate-500', icon: <AlertTriangle size={32}/>, advice: 'Датчики не отвечают' };
  if (pm25 <= 12) return { label: 'Отлично', color: 'bg-emerald-100 text-emerald-700', icon: <ShieldCheck size={32}/>, advice: 'Идеальное время для прогулок и спорта.' };
  if (pm25 <= 35) return { label: 'Нормально', color: 'bg-yellow-100 text-yellow-700', icon: <CheckCircle2 size={32}/>, advice: 'Качество приемлемое. Можно проветривать.' };
  if (pm25 <= 55) return { label: 'Вредно для уязвимых', color: 'bg-orange-100 text-orange-700', icon: <AlertTriangle size={32}/>, advice: 'Астматикам лучше закрыть окна.' };
  return { label: 'Опасно', color: 'bg-red-100 text-red-700', icon: <AlertTriangle size={32}/>, advice: 'Избегайте улицы. Включите очиститель воздуха.' };
};

export default function App() {
  // --- S T A T E ---
  const [activeView, setActiveView] = useState<'dashboard' | 'data' | 'logs'>('dashboard');
  const [cities, setCities] = useState<City[]>([]);
  const [selectedCityName, setSelectedCityName] = useState<string>('');
  const [data, setData] = useState<UnifiedDataPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  
  // UI State
  const [showMLForecast, setShowMLForecast] = useState(true);
  const [correlationMetric, setCorrelationMetric] = useState<'temperature' | 'windSpeed' | 'humidity'>('temperature');

  // --- L O G G I N G ---
  const addLog = useCallback((type: LogEntry['type'], message: string) => {
    setLogs(prev => [{
      id: Math.random().toString(36).substr(2, 9),
      time: new Date().toLocaleTimeString('ru-RU'),
      type,
      message
    }, ...prev]);
  }, []);

  // --- I N I T ---
  useEffect(() => {
    fetchCities().then(list => {
        setCities(list);
        if (list.length > 0) setSelectedCityName(list[0].name);
        addLog('success', `Загружен справочник городов: ${list.length} записей`);
      }).catch(err => addLog('error', `Ошибка загрузки городов: ${err.message}`));
  }, [addLog]);

  // --- L O A D   D A T A ---
  const loadData = async () => {
    if (!selectedCityName) return;
    setLoading(true);
    addLog('info', `ETL Request: Получение данных для ${selectedCityName}...`);
    try {
      const result = await fetchDashboardData(selectedCityName);
      const sorted = result.reverse(); // Хронология для графиков
      setData(sorted);
      addLog('success', `Data Ingest: Получено ${sorted.length} точек данных.`);
    } catch (err: any) {
      addLog('error', `API Error: ${err.message}`);
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [selectedCityName]);

  // --- C A L C U L A T E D   S T A T S ---
  const stats = useMemo(() => {
    if (data.length === 0) return null;
    const last = data[data.length - 1];
    
    // Observability metrics
    const lastUpdate = new Date(last.timestamp);
    const now = new Date();
    const hoursDiff = (now.getTime() - lastUpdate.getTime()) / (1000 * 3600);
    const isFresh = hoursDiff < 24; // Данные свежее 24 часов
    
    const missingPM = data.filter(d => d.pm25 === null).length;
    const qualityScore = Math.max(0, 100 - (missingPM / data.length * 100)).toFixed(0);

    return {
      current: last,
      isFresh,
      qualityScore,
      totalRows: data.length,
      status: getAirQualityStatus(last.pm25)
    };
  }, [data]);

  // --- R E N D E R ---
  return (
    <div className="flex h-screen bg-slate-100 font-sans text-slate-900 overflow-hidden">
      
      {/* === S I D E B A R === */}
      <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shadow-2xl z-20 shrink-0">
        <div className="h-16 flex items-center px-6 border-b border-slate-800 bg-slate-950">
          <Activity className="h-6 w-6 text-indigo-500 mr-3" />
          <div>
            <span className="font-bold text-lg text-white tracking-tight block leading-none">EcoSense</span>
            <span className="text-[10px] text-slate-500 font-mono uppercase">Analytics v2.0</span>
          </div>
        </div>

        {/* City Selector */}
        <div className="p-4 border-b border-slate-800">
          <label className="text-[10px] font-bold text-slate-500 uppercase mb-2 block tracking-wider">Локация</label>
          <div className="relative group">
            <MapPin className="absolute left-3 top-2.5 h-4 w-4 text-slate-400 group-hover:text-indigo-400 transition-colors" />
            <select 
              className="w-full bg-slate-800 border border-slate-700 text-white text-sm rounded-lg pl-9 pr-3 py-2 focus:ring-2 focus:ring-indigo-500 outline-none appearance-none cursor-pointer hover:bg-slate-750 transition-colors"
              value={selectedCityName}
              onChange={(e) => setSelectedCityName(e.target.value)}
              disabled={loading}
            >
              {cities.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
            </select>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-6 px-3 space-y-1">
          <NavItem icon={<LayoutDashboard/>} label="Дашборд" active={activeView === 'dashboard'} onClick={() => setActiveView('dashboard')} />
          <NavItem icon={<TableIcon/>} label="Данные" active={activeView === 'data'} onClick={() => setActiveView('data')} />
          <NavItem icon={<ScrollText/>} label="Логи ETL" active={activeView === 'logs'} onClick={() => setActiveView('logs')} badge={logs.filter(l => l.type === 'error').length} />
        </nav>

        {/* System Health Footer */}
        <div className="p-4 bg-slate-950 border-t border-slate-800 text-[11px] space-y-2">
          <div className="flex justify-between items-center">
             <span className="text-slate-500 flex items-center gap-1"><Server size={10}/> API Status</span>
             <span className="text-emerald-400 font-medium">Online</span>
          </div>
          <div className="flex justify-between items-center">
             <span className="text-slate-500 flex items-center gap-1"><Database size={10}/> DB Connection</span>
             <span className="text-blue-400 font-medium">Active</span>
          </div>
        </div>
      </aside>

      {/* === M A I N   C O N T E N T === */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden relative">
        
        {/* Header */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 shadow-sm z-10 shrink-0">
          <div className="flex items-center gap-4">
             <h1 className="text-xl font-bold text-slate-800">
               {activeView === 'dashboard' && 'Мониторинг окружающей среды'}
               {activeView === 'data' && 'Реестр измерений'}
               {activeView === 'logs' && 'Журнал событий'}
             </h1>
          </div>
          
          <div className="flex items-center gap-3">
             <button 
                onClick={loadData}
                disabled={loading}
                className={`flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-all shadow-md shadow-indigo-100 ${loading ? 'opacity-80' : ''}`}
              >
                <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                {loading ? 'Обновление...' : 'Обновить данные'}
              </button>
          </div>
        </header>

        {/* Scrollable Area */}
        <div className="flex-1 overflow-auto bg-slate-50 p-6 scrollbar-thin scrollbar-thumb-slate-300">
          
          {/* V I E W :  D A S H B O A R D */}
          {activeView === 'dashboard' && (
            <div className="max-w-7xl mx-auto space-y-6">
              
              {/* 1. OBSERVABILITY STRIP (Status Bar) */}
              <div className="flex items-center gap-6 text-sm text-slate-600 bg-white px-4 py-2 rounded-lg border border-slate-200 shadow-sm">
                 <span className="font-bold text-slate-400 text-xs uppercase tracking-wider">Качество данных:</span>
                 <div className="flex items-center gap-2">
                    <Wifi size={16} className={stats ? 'text-emerald-500' : 'text-red-500'} />
                    <span>Источник: <span className="font-medium text-slate-900">Open-Meteo API</span></span>
                 </div>
                 <div className="h-4 w-px bg-slate-200"></div>
                 <div className="flex items-center gap-2">
                    <Clock size={16} className={stats?.isFresh ? 'text-emerald-500' : 'text-amber-500'} />
                    <span>Актуальность: <span className="font-medium text-slate-900">{stats?.isFresh ? 'Свежие (<24ч)' : 'Устаревшие'}</span></span>
                 </div>
                 <div className="h-4 w-px bg-slate-200"></div>
                 <div className="flex items-center gap-2">
                    <ShieldCheck size={16} className={Number(stats?.qualityScore) > 90 ? 'text-emerald-500' : 'text-amber-500'} />
                    <span>Полнота: <span className="font-medium text-slate-900">{stats?.qualityScore ?? 0}%</span></span>
                 </div>
              </div>

              {/* 2. HERO SECTION: Health & Weather */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                 {/* Left: Health Widget */}
                 <div className={`md:col-span-2 rounded-xl p-6 border ${stats?.status.color} border-opacity-20 flex items-center gap-6 shadow-sm transition-all`}>
                    <div className="p-4 bg-white bg-opacity-40 rounded-full backdrop-blur-sm">
                       {stats?.status.icon}
                    </div>
                    <div>
                       <div className="flex items-center gap-3 mb-1">
                          <h2 className="text-2xl font-bold">{stats?.status.label}</h2>
                          <span className="text-sm font-mono opacity-80 border border-current px-2 rounded-full">PM2.5: {stats?.current.pm25 ?? '--'}</span>
                       </div>
                       <p className="opacity-90 font-medium max-w-lg">{stats?.status.advice}</p>
                    </div>
                 </div>

                 {/* Right: Weather Context */}
                 <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Текущая погода</h3>
                    <div className="flex justify-between items-end">
                       <div>
                          <div className="flex items-center gap-2 text-3xl font-bold text-slate-800">
                             <Thermometer className="text-indigo-500" size={28}/>
                             {stats?.current.temperature ?? '--'}°C
                          </div>
                          <div className="flex items-center gap-4 mt-3 text-sm text-slate-500">
                             <span className="flex items-center gap-1"><Droplets size={14}/> {stats?.current.humidity}%</span>
                             <span className="flex items-center gap-1"><Wind size={14}/> {stats?.current.windSpeed} km/h</span>
                          </div>
                       </div>
                    </div>
                 </div>
              </div>

              {/* 3. MAIN CHART: Trends + ML Toggle */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                 <div className="flex justify-between items-center mb-6">
                    <div className="flex items-center gap-2">
                       <Activity className="text-indigo-600" size={20}/>
                       <h3 className="font-bold text-slate-800">Динамика загрязнения и ML-прогноз</h3>
                    </div>
                    {/* ML Toggle */}
                    <label className="flex items-center gap-2 cursor-pointer bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 transition-colors">
                       <input 
                         type="checkbox" 
                         checked={showMLForecast} 
                         onChange={(e) => setShowMLForecast(e.target.checked)} 
                         className="rounded text-indigo-600 focus:ring-indigo-500"
                       />
                       <span className="text-sm font-medium text-slate-600">Показать AI прогноз</span>
                       <BrainCircuit size={14} className="text-purple-500"/>
                    </label>
                 </div>
                 
                 <div className="h-[350px]">
                    {/* Передаем проп, чтобы график знал, рисовать ли линию прогноза. 
                        Примечание: TrendsChart должен уметь это обрабатывать, или мы фильтруем данные */}
                    {data.length > 0 
                      ? <TrendsChart data={data} showPrediction={showMLForecast} /> 
                      : <div className="h-full flex items-center justify-center text-slate-400">Нет данных</div>
                    }
                 </div>
              </div>

              {/* 4. BOTTOM GRID: Heatmap & Correlation */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                 {/* Heatmap */}
                 <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm h-[400px] flex flex-col">
                    <h3 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
                      <TableIcon size={18} className="text-slate-400"/>
                      Тепловая карта рисков
                    </h3>
                    <div className="flex-1 min-h-0">
                      {data.length > 0 ? <RiskHeatmap data={data} /> : null}
                    </div>
                 </div>

                 {/* Interactive Correlation */}
                 <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm h-[400px] flex flex-col">
                    <div className="flex justify-between items-center mb-4">
                       <h3 className="font-bold text-slate-800">Факторы влияния</h3>
                       {/* Controls for Drill-down */}
                       <div className="flex bg-slate-100 rounded-lg p-1">
                          {(['temperature', 'windSpeed', 'humidity'] as const).map(m => (
                             <button
                                key={m}
                                onClick={() => setCorrelationMetric(m)}
                                className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                                   correlationMetric === m 
                                   ? 'bg-white text-indigo-600 shadow-sm' 
                                   : 'text-slate-500 hover:text-slate-700'
                                }`}
                             >
                                {m === 'temperature' ? 'Темп' : m === 'windSpeed' ? 'Ветер' : 'Влажн'}
                             </button>
                          ))}
                       </div>
                    </div>
                    <div className="flex-1 min-h-0 relative">
                      {data.length > 0 
                        ? <CorrelationChart data={data} xKey={correlationMetric} /> 
                        : null
                      }
                      <p className="absolute bottom-0 right-0 text-[10px] text-slate-400">
                        * Анализ зависимости PM2.5 от выбранного фактора
                      </p>
                    </div>
                 </div>
              </div>

            </div>
          )}

          {/* V I E W :  D A T A   T A B L E */}
          {activeView === 'data' && (
             <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden max-w-7xl mx-auto flex flex-col h-[calc(100vh-140px)]">
                <div className="px-6 py-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
                   <h3 className="font-semibold text-slate-700">Сырые данные (БД)</h3>
                   <span className="text-xs bg-slate-200 text-slate-600 px-2 py-1 rounded font-mono">dm_dashboard_analytics</span>
                </div>
                <div className="flex-1 overflow-auto">
                   <table className="w-full text-sm text-left">
                      <thead className="bg-slate-50 text-slate-500 sticky top-0 z-10 font-medium shadow-sm">
                         <tr>
                            <th className="px-6 py-3">Timestamp</th>
                            <th className="px-6 py-3">PM 2.5</th>
                            <th className="px-6 py-3">ML Prediction</th>
                            <th className="px-6 py-3">Температура</th>
                            <th className="px-6 py-3">Влажность</th>
                            <th className="px-6 py-3">Ветер</th>
                         </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                         {data.map((row, i) => (
                            <tr key={i} className="hover:bg-slate-50 transition-colors">
                               <td className="px-6 py-3 font-mono text-slate-600 text-xs">{row.displayTime}</td>
                               <td className="px-6 py-3">
                                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${row.pm25 === null ? 'bg-slate-100' : row.pm25 > 25 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
                                     {row.pm25 ?? 'NULL'}
                                  </span>
                               </td>
                               <td className="px-6 py-3 text-indigo-600 font-mono text-xs">{row.predictedPM25 ?? '-'}</td>
                               <td className="px-6 py-3 text-slate-600">{row.temperature}°</td>
                               <td className="px-6 py-3 text-slate-600">{row.humidity}%</td>
                               <td className="px-6 py-3 text-slate-600">{row.windSpeed}</td>
                            </tr>
                         ))}
                      </tbody>
                   </table>
                </div>
             </div>
          )}

          {/* V I E W :  L O G S */}
          {activeView === 'logs' && (
             <div className="max-w-4xl mx-auto space-y-6">
                <div className="bg-slate-900 rounded-lg p-6 shadow-lg border border-slate-700 text-slate-300 font-mono text-sm">
                   <div className="flex items-center gap-2 text-indigo-400 mb-4 border-b border-slate-700 pb-3">
                      <Terminal size={18} />
                      <span className="font-bold">ETL Control Plane</span>
                   </div>
                   <div className="space-y-4">
                      <div>
                         <p className="text-xs text-slate-500 mb-1 uppercase tracking-wider">Обновить данные (Backend)</p>
                         <div className="bg-black/50 p-3 rounded border border-slate-800 flex justify-between">
                            <code>python etl.py</code>
                         </div>
                      </div>
                      <div>
                         <p className="text-xs text-slate-500 mb-1 uppercase tracking-wider">Запуск сервера API</p>
                         <div className="bg-black/50 p-3 rounded border border-slate-800">
                            <code>python server.py --reload</code>
                         </div>
                      </div>
                   </div>
                </div>

                <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                   <div className="px-6 py-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
                      <h3 className="font-semibold text-slate-700">Журнал операций (Frontend)</h3>
                      <button onClick={() => setLogs([])} className="text-xs text-indigo-600 hover:underline">Очистить</button>
                   </div>
                   <div className="divide-y divide-slate-100 max-h-[500px] overflow-auto">
                      {logs.map((log) => (
                         <div key={log.id} className="px-6 py-3 flex gap-4 text-sm hover:bg-slate-50">
                            <span className="text-slate-400 font-mono text-xs w-20 pt-1">{log.time}</span>
                            <div className="flex-1">
                               <span className={`inline-block w-2 h-2 rounded-full mr-2 ${log.type === 'error' ? 'bg-red-500' : log.type === 'success' ? 'bg-emerald-500' : 'bg-blue-400'}`} />
                               <span className={log.type === 'error' ? 'text-red-700' : 'text-slate-700'}>{log.message}</span>
                            </div>
                         </div>
                      ))}
                      {logs.length === 0 && <div className="p-8 text-center text-slate-400">Нет записей</div>}
                   </div>
                </div>
             </div>
          )}

        </div>
      </main>
    </div>
  );
}

// --- S U B C O M P O N E N T S ---

function NavItem({ icon, label, active, onClick, badge }: any) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center justify-between px-4 py-3 text-sm font-medium transition-all duration-200 border-l-4 ${
        active 
          ? 'bg-slate-800 border-indigo-500 text-white shadow-inner' 
          : 'border-transparent text-slate-400 hover:bg-slate-800 hover:text-slate-200'
      }`}
    >
      <div className="flex items-center gap-3">
        {React.cloneElement(icon, { size: 18, className: active ? 'text-indigo-400' : 'opacity-70' })}
        <span>{label}</span>
      </div>
      {badge ? (
        <span className="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px]">
          {badge}
        </span>
      ) : null}
    </button>
  );
}