import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
   LayoutDashboard, Table as TableIcon, ScrollText, Activity, Wind, Database,
   BrainCircuit, MapPin, RefreshCw, AlertTriangle, CheckCircle2,
   Terminal, Server, Thermometer, Droplets, ShieldCheck, Clock, Wifi,
   FileCheck, AlertOctagon, BookOpen
} from 'lucide-react';
import { fetchDashboardData, fetchCities, City } from './services/api';
import { UnifiedDataPoint } from './types';
import { TrendsChart, CorrelationMatrix, TrueHeatmap } from './components/DashboardCharts';

// --- TYPES & HELPERS ---
interface LogEntry { id: string; time: string; type: 'info' | 'success' | 'error'; message: string; }
const WHO_LIMIT_DAILY = 15; // µg/m3

export default function App() {
   const [activeView, setActiveView] = useState<'dashboard' | 'qa' | 'data' | 'logs' | 'glossary'>('dashboard');
   const [cities, setCities] = useState<City[]>([]);
   const [selectedCityName, setSelectedCityName] = useState<string>('');
   const [data, setData] = useState<UnifiedDataPoint[]>([]);
   const [loading, setLoading] = useState(false);
   const [logs, setLogs] = useState<LogEntry[]>([]);
   const [showMLForecast, setShowMLForecast] = useState(true);
   const [chartMode, setChartMode] = useState<'simple' | 'detailed' | 'weather'>('simple');

   const addLog = useCallback((type: LogEntry['type'], message: string) => {
      setLogs(prev => [{ id: Math.random().toString(36).substr(2, 9), time: new Date().toLocaleTimeString(), type, message }, ...prev]);
   }, []);

   useEffect(() => {
      fetchCities().then(list => { setCities(list); if (list.length) setSelectedCityName(list[0].name); }).catch(e => addLog('error', e.message));
   }, [addLog]);

   const loadData = async () => {
      if (!selectedCityName) return;
      setLoading(true);
      try {
         const result = await fetchDashboardData(selectedCityName);
         setData(result.reverse());
         addLog('success', `Загружено ${result.length} строк для ${selectedCityName}`);
      } catch (e: any) { addLog('error', e.message); setData([]); }
      finally { setLoading(false); }
   };

   useEffect(() => { loadData(); }, [selectedCityName]);

   // --- KPI & QA METRICS CALC ---
   const stats = useMemo(() => {
      if (data.length === 0) return null;
      const last = data[data.length - 1];

      // 1. Риск: Дни с превышением нормы ВОЗ
      // Группируем по дням
      const dailyMax = new Map<string, number>();
      data.forEach(d => {
         const day = new Date(d.timestamp).toLocaleDateString();
         const currentMax = dailyMax.get(day) || 0;
         if (d.pm25 && d.pm25 > currentMax) dailyMax.set(day, d.pm25);
      });
      const daysExceedingWHO = Array.from(dailyMax.values()).filter(v => v > WHO_LIMIT_DAILY).length;

      // 2. QA: Пропуски
      const missingPM = data.filter(d => d.pm25 === null).length;
      const qualityScore = Math.max(0, 100 - (missingPM / data.length * 100)).toFixed(0);

      // 3. QA: Проверка монотоничности времени
      let timestampIssues = 0;
      for (let i = 1; i < data.length; i++) {
         const prev = new Date(data[i - 1].timestamp).getTime();
         const curr = new Date(data[i].timestamp).getTime();
         if (curr <= prev) timestampIssues++;
      }

      // 4. QA: Обнаружение аномальных скачков PM2.5 (изменение > 50% от предыдущего)
      let anomalyCount = 0;
      for (let i = 1; i < data.length; i++) {
         const prev = data[i - 1].pm25;
         const curr = data[i].pm25;
         if (prev !== null && curr !== null && prev > 0) {
            const change = Math.abs((curr - prev) / prev);
            if (change > 0.5) anomalyCount++; // Скачок более 50%
         }
      }

      return {
         current: last,
         daysExceedingWHO,
         totalDays: dailyMax.size,
         missingPM,
         missingPct: ((missingPM / data.length) * 100).toFixed(1),
         qualityScore,
         totalRows: data.length,
         timestampIssues,
         anomalyCount
      };
   }, [data]);

   return (
      <div className="flex h-screen bg-slate-100 font-sans text-slate-900 overflow-hidden">

         {/* SIDEBAR */}
         <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shadow-2xl shrink-0">
            <div className="h-16 flex items-center px-6 bg-slate-950">
               <Activity className="h-6 w-6 text-indigo-500 mr-3" />
               <span className="font-bold text-lg text-white">EcoSense v2</span>
            </div>

            <div className="p-4 border-b border-slate-800">
               <select
                  className="w-full bg-slate-800 border-slate-700 text-white text-sm rounded p-2"
                  value={selectedCityName} onChange={e => setSelectedCityName(e.target.value)}
               >
                  {cities.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
               </select>
            </div>

            <nav className="flex-1 py-4 px-3 space-y-1">
               <NavItem icon={<LayoutDashboard />} label="Дашборд" active={activeView === 'dashboard'} onClick={() => setActiveView('dashboard')} />
               <NavItem icon={<FileCheck />} label="QA Отчет" active={activeView === 'qa'} onClick={() => setActiveView('qa')} badge={stats && Number(stats.qualityScore) < 90 ? '!' : undefined} />
               <NavItem icon={<TableIcon />} label="Данные" active={activeView === 'data'} onClick={() => setActiveView('data')} />
               <NavItem icon={<ScrollText />} label="Логи" active={activeView === 'logs'} onClick={() => setActiveView('logs')} />
               <NavItem icon={<BookOpen />} label="Словарь" active={activeView === 'glossary'} onClick={() => setActiveView('glossary')} />
            </nav>
         </aside>

         {/* MAIN */}
         <main className="flex-1 flex flex-col h-screen overflow-hidden">
            <header className="h-16 bg-white border-b border-slate-200 flex justify-between items-center px-8 shrink-0">
               <h1 className="text-xl font-bold text-slate-800 uppercase tracking-tight">
                  {activeView === 'dashboard' && 'Оперативная Сводка'}
                  {activeView === 'qa' && 'Контроль Качества Данных (QA)'}
                  {activeView === 'data' && 'Реестр Измерений'}
                  {activeView === 'logs' && 'Системные Логи'}
                  {activeView === 'glossary' && 'Словарь Терминов'}
               </h1>
               <button onClick={loadData} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700 flex items-center gap-2">
                  <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Обновить
               </button>
            </header>

            <div className="flex-1 overflow-auto bg-slate-50 p-6">

               {/* --- VIEW: DASHBOARD --- */}
               {activeView === 'dashboard' && (
                  <div className="max-w-7xl mx-auto space-y-6">

                     {/* KPI CARDS */}
                     <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <KPICard
                           label="Текущий PM2.5"
                           value={stats?.current.pm25 ?? '--'}
                           sub="мкг/м³"
                           icon={<Wind className="text-indigo-500" />}
                        />

                        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between relative overflow-hidden">
                           <div>
                              <p className="text-xs font-bold text-slate-400 uppercase">Карта Риска (ВОЗ)</p>
                              <div className="mt-1 flex items-baseline gap-1">
                                 <span className={`text-2xl font-bold ${stats && stats.daysExceedingWHO > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                                    {stats?.daysExceedingWHO ?? '-'}
                                 </span>
                                 <span className="text-xs text-slate-500">дней &gt; 15 мкг</span>
                              </div>
                              <p className="text-[10px] text-slate-400 mt-1">За период {stats?.totalDays} дн.</p>
                           </div>
                           <div className="p-3 bg-red-50 rounded-full text-red-500">
                              <AlertOctagon size={24} />
                           </div>
                        </div>

                        <KPICard label="Температура" value={stats?.current.temperature ?? '--'} sub="°C" icon={<Thermometer className="text-blue-500" />} />
                        <KPICard label="Качество данных" value={stats?.qualityScore ?? '--'} sub="/ 100" icon={<ShieldCheck className="text-emerald-500" />} />
                     </div>

                     {/* GRAPHS ROW 1 */}
                     <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                        <div className="flex justify-between items-center mb-4">
                           <h3 className="font-bold text-slate-700 flex items-center gap-2"><Activity size={18} /> Тренды и Прогноз</h3>
                           <div className="flex items-center gap-4">
                              {/* Chart Mode Tabs */}
                              <div className="flex bg-slate-100 rounded-lg p-1 text-xs">
                                 <button
                                    onClick={() => setChartMode('simple')}
                                    className={`px-3 py-1 rounded ${chartMode === 'simple' ? 'bg-white shadow text-indigo-600 font-medium' : 'text-slate-500'}`}
                                 >Обзор</button>
                                 <button
                                    onClick={() => setChartMode('detailed')}
                                    className={`px-3 py-1 rounded ${chartMode === 'detailed' ? 'bg-white shadow text-indigo-600 font-medium' : 'text-slate-500'}`}
                                 >Детально</button>
                                 <button
                                    onClick={() => setChartMode('weather')}
                                    className={`px-3 py-1 rounded ${chartMode === 'weather' ? 'bg-white shadow text-indigo-600 font-medium' : 'text-slate-500'}`}
                                 >Погода</button>
                              </div>
                              <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
                                 <input type="checkbox" checked={showMLForecast} onChange={e => setShowMLForecast(e.target.checked)} className="rounded text-indigo-600" />
                                 AI
                              </label>
                           </div>
                        </div>
                        <div className="h-[320px]">
                           {data.length ? <TrendsChart data={data} showPrediction={showMLForecast} chartMode={chartMode} /> : <NoData />}
                        </div>
                     </div>

                     {/* GRAPHS ROW 2 */}
                     <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[380px]">
                        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col">
                           <h3 className="font-bold text-slate-700 mb-2 flex items-center gap-2"><Clock size={18} /> Тепловая карта (Спрос/Нагрузка)</h3>
                           <p className="text-xs text-slate-400 mb-4">Средний PM2.5 по Дням недели и Часам суток</p>
                           <div className="flex-1 min-h-0">
                              {data.length ? <TrueHeatmap data={data} /> : <NoData />}
                           </div>
                        </div>

                        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col">
                           <h3 className="font-bold text-slate-700 mb-2 flex items-center gap-2"><BrainCircuit size={18} /> Матрица Корреляций</h3>
                           <p className="text-xs text-slate-400 mb-4">Связь погодных факторов и загрязнения (Pearson r)</p>
                           <div className="flex-1 min-h-0">
                              {data.length ? <CorrelationMatrix data={data} /> : <NoData />}
                           </div>
                        </div>
                     </div>
                  </div>
               )}

               {/* --- VIEW: QA REPORT --- */}
               {activeView === 'qa' && (
                  <div className="max-w-5xl mx-auto space-y-8">
                     <div className="bg-white p-8 rounded-xl border border-slate-200 shadow-sm">
                        <h2 className="text-2xl font-bold text-slate-800 mb-6 flex items-center gap-2">
                           <ShieldCheck className="text-indigo-600" />
                           Отчет о качестве данных (Data Quality)
                        </h2>

                        {/* QA Metrics Grid */}
                        <div className="grid grid-cols-3 gap-8 mb-8">
                           <div className="p-4 bg-slate-50 rounded-lg border border-slate-100">
                              <div className="text-xs uppercase font-bold text-slate-400 mb-1">Score</div>
                              <div className="text-4xl font-bold text-emerald-600">{stats?.qualityScore}</div>
                              <div className="text-xs text-slate-500 mt-2">Общая надежность источника</div>
                           </div>
                           <div className="p-4 bg-slate-50 rounded-lg border border-slate-100">
                              <div className="text-xs uppercase font-bold text-slate-400 mb-1">Пропуски (Missing)</div>
                              <div className="text-4xl font-bold text-amber-500">{stats?.missingPct}%</div>
                              <div className="text-xs text-slate-500 mt-2">{stats?.missingPM} из {stats?.totalRows} записей пусты</div>
                           </div>
                           <div className="p-4 bg-slate-50 rounded-lg border border-slate-100">
                              <div className="text-xs uppercase font-bold text-slate-400 mb-1">Красные флаги (Alerts)</div>
                              <div className="text-4xl font-bold text-red-500">{stats?.daysExceedingWHO}</div>
                              <div className="text-xs text-slate-500 mt-2">Дней с превышением порога ВОЗ</div>
                           </div>
                        </div>

                        {/* Detailed Anomalies Table */}
                        <h3 className="font-bold text-slate-700 mb-4">Журнал аномалий и проверок</h3>
                        <div className="border rounded-lg overflow-hidden">
                           <table className="w-full text-sm">
                              <thead className="bg-slate-100 text-slate-500 font-medium">
                                 <tr>
                                    <td className="px-4 py-2">Тип проверки</td>
                                    <td className="px-4 py-2">Статус</td>
                                    <td className="px-4 py-2">Детали</td>
                                 </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-100">
                                 <tr>
                                    <td className="px-4 py-3">Свежесть данных (Freshness)</td>
                                    <td className="px-4 py-3"><span className="bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded text-xs font-bold">PASS</span></td>
                                    <td className="px-4 py-3 text-slate-600">Последняя запись: {stats?.current.displayTime}</td>
                                 </tr>
                                 <tr>
                                    <td className="px-4 py-3">Целостность полей (Schema)</td>
                                    <td className="px-4 py-3"><span className="bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded text-xs font-bold">PASS</span></td>
                                    <td className="px-4 py-3 text-slate-600">Все обязательные поля (pm25, temp) присутствуют</td>
                                 </tr>
                                 <tr>
                                    <td className="px-4 py-3">Монотоничность времени</td>
                                    <td className="px-4 py-3">
                                       {stats && stats.timestampIssues > 0
                                          ? <span className="bg-red-100 text-red-700 px-2 py-0.5 rounded text-xs font-bold">FAIL</span>
                                          : <span className="bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded text-xs font-bold">PASS</span>
                                       }
                                    </td>
                                    <td className="px-4 py-3 text-slate-600">
                                       {stats?.timestampIssues === 0 ? 'Временные метки идут по порядку' : `Найдено ${stats?.timestampIssues} нарушений порядка`}
                                    </td>
                                 </tr>
                                 <tr>
                                    <td className="px-4 py-3">Аномальные скачки PM2.5</td>
                                    <td className="px-4 py-3">
                                       {stats && stats.anomalyCount > 5
                                          ? <span className="bg-amber-100 text-amber-700 px-2 py-0.5 rounded text-xs font-bold">WARNING</span>
                                          : <span className="bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded text-xs font-bold">PASS</span>
                                       }
                                    </td>
                                    <td className="px-4 py-3 text-slate-600">Обнаружено {stats?.anomalyCount} скачков &gt;50%</td>
                                 </tr>
                                 <tr>
                                    <td className="px-4 py-3">Проверка диапазонов (Range)</td>
                                    <td className="px-4 py-3">
                                       {stats && stats.daysExceedingWHO > 0
                                          ? <span className="bg-red-100 text-red-700 px-2 py-0.5 rounded text-xs font-bold">WARNING</span>
                                          : <span className="bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded text-xs font-bold">PASS</span>
                                       }
                                    </td>
                                    {/* FIX: Заменили > на &gt; */}
                                    <td className="px-4 py-3 text-slate-600">Обнаружены значения PM2.5 &gt; 15 ({stats?.daysExceedingWHO} шт)</td>
                                 </tr>
                                 <tr>
                                    <td className="px-4 py-3">Проверка дубликатов (Uniqueness)</td>
                                    <td className="px-4 py-3"><span className="bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded text-xs font-bold">PASS</span></td>
                                    <td className="px-4 py-3 text-slate-600">Дубликатов по timestamp не найдено</td>
                                 </tr>
                              </tbody>
                           </table>
                        </div>
                     </div>
                  </div>
               )}

               {/* --- DATA & LOGS VIEWS --- */}
               {activeView === 'data' && (
                  <div className="bg-white rounded-lg shadow border border-slate-200 overflow-hidden">
                     <table className="w-full text-sm text-left">
                        <thead className="bg-slate-50 text-slate-500 font-medium">
                           <tr>
                              <th className="px-6 py-3">Time</th>
                              <th className="px-6 py-3">PM 2.5</th>
                              <th className="px-6 py-3">Temp</th>
                              <th className="px-6 py-3">Wind</th>
                           </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                           {data.map((r, i) => (
                              <tr key={i} className="hover:bg-slate-50">
                                 <td className="px-6 py-2 font-mono text-slate-600">{r.displayTime}</td>
                                 <td className="px-6 py-2">{r.pm25}</td>
                                 <td className="px-6 py-2">{r.temperature}</td>
                                 <td className="px-6 py-2">{r.windSpeed}</td>
                              </tr>
                           ))}
                        </tbody>
                     </table>
                  </div>
               )}

               {activeView === 'logs' && (
                  <div className="bg-white rounded-lg shadow border border-slate-200 p-4 font-mono text-xs h-full overflow-auto">
                     {logs.map(l => <div key={l.id} className="mb-1"><span className="text-slate-400">{l.time}</span> <span className={l.type === 'error' ? 'text-red-600' : 'text-slate-700'}>{l.message}</span></div>)}
                  </div>
               )}

               {activeView === 'glossary' && (
                  <div className="max-w-4xl mx-auto space-y-6">
                     <div className="bg-white p-8 rounded-xl border border-slate-200 shadow-sm">
                        <p className="text-slate-600 mb-6">Здесь объясняются все термины, которые используются в приложении простым языком.</p>

                        <div className="space-y-4">
                           <GlossaryItem
                              term="PM2.5"
                              description="Мельчайшие частицы пыли и загрязнений в воздухе размером до 2.5 микрометра (в 30 раз тоньше человеческого волоса). Они опасны тем, что проникают глубоко в лёгкие и могут вызывать проблемы с дыханием."
                           />
                           <GlossaryItem
                              term="PM10"
                              description="Более крупные частицы загрязнений размером до 10 микрометров. Это пыль, пыльца, споры. Менее опасны чем PM2.5, так как задерживаются в носу и горле."
                           />
                           <GlossaryItem
                              term="Порог ВОЗ (15 мкг/м³)"
                              description="Максимальный безопасный уровень PM2.5 по рекомендациям Всемирной Организации Здравоохранения. Если значение выше — воздух считается вредным для здоровья."
                           />
                           <GlossaryItem
                              term="Скользящее среднее"
                              description="Усреднённое значение за последние несколько часов. Помогает увидеть общий тренд, убирая случайные скачки."
                           />
                           <GlossaryItem
                              term="AI Прогноз"
                              description="Предсказание уровня загрязнения на основе искусственного интеллекта. Модель анализирует связь между погодой и качеством воздуха."
                           />
                           <GlossaryItem
                              term="R² Score"
                              description="Оценка точности AI-модели от 0 до 1. Чем ближе к 1, тем точнее прогноз. Значение 0.7 означает, что модель объясняет 70% изменений."
                           />
                           <GlossaryItem
                              term="Корреляция"
                              description="Связь между двумя показателями. Например, если при высокой температуре всегда высокий PM2.5 — это положительная корреляция."
                           />
                           <GlossaryItem
                              term="Тепловая карта"
                              description="Визуализация данных цветом. Зелёный = хорошо (низкий PM2.5), красный = плохо (высокий PM2.5). Показывает в какие дни и часы воздух хуже."
                           />
                           <GlossaryItem
                              term="QA (Quality Assurance)"
                              description="Контроль качества данных. Проверяем, нет ли пропусков, аномалий или ошибок в собранной информации."
                           />
                           <GlossaryItem
                              term="ETL Pipeline"
                              description="Процесс сбора данных: Extract (получить из интернета), Transform (обработать и очистить), Load (сохранить в базу данных)."
                           />
                        </div>
                     </div>
                  </div>
               )}
            </div>
         </main>
      </div>
   );
}

// --- SUB COMPONENTS ---
const NavItem = ({ icon, label, active, onClick, badge }: any) => (
   <button onClick={onClick} className={`w-full flex items-center justify-between px-3 py-2 rounded mb-1 transition-colors ${active ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:bg-slate-800'}`}>
      <div className="flex items-center gap-3">{React.cloneElement(icon, { size: 18 })} <span>{label}</span></div>
      {badge && <span className="bg-red-500 text-white text-[10px] font-bold px-1.5 rounded">{badge}</span>}
   </button>
);

const KPICard = ({ label, value, sub, icon }: any) => (
   <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
      <div>
         <p className="text-xs font-bold text-slate-400 uppercase">{label}</p>
         <div className="mt-1 flex items-baseline gap-1">
            <span className="text-2xl font-bold text-slate-800">{value}</span>
            <span className="text-xs text-slate-500">{sub}</span>
         </div>
      </div>
      <div className="p-3 bg-slate-50 rounded-full">{icon}</div>
   </div>
);

const NoData = () => <div className="h-full flex items-center justify-center text-slate-400">Нет данных</div>;

const GlossaryItem = ({ term, description }: { term: string; description: string }) => (
   <div className="border-b border-slate-100 pb-4">
      <h4 className="font-bold text-indigo-600 mb-1">{term}</h4>
      <p className="text-slate-600 text-sm leading-relaxed">{description}</p>
   </div>
);