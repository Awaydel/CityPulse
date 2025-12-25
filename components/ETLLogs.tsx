import React, { useEffect, useRef } from 'react';
import { LogEntry } from '../types';

interface ETLLogsProps {
  logs: LogEntry[];
}

const ETLLogs: React.FC<ETLLogsProps> = ({ logs }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="bg-slate-900 text-slate-200 rounded-lg shadow-lg border border-slate-700 overflow-hidden flex flex-col h-full">
      <div className="bg-slate-800 px-4 py-2 border-b border-slate-700 flex justify-between items-center">
        <span className="font-mono text-xs uppercase tracking-wider text-slate-400">Логи Оркестратора</span>
        <div className="flex gap-1">
            <div className="w-2 h-2 rounded-full bg-red-500"></div>
            <div className="w-2 h-2 rounded-full bg-yellow-500"></div>
            <div className="w-2 h-2 rounded-full bg-green-500"></div>
        </div>
      </div>
      <div ref={scrollRef} className="p-4 font-mono text-xs space-y-3 overflow-y-auto max-h-60 flex-1">
        {logs.length === 0 && <span className="text-slate-500 italic">Ожидание запуска пайплайна...</span>}
        {logs.map((log) => (
          <div key={log.id} className="flex gap-3 items-start">
            <span className="text-slate-500 shrink-0 mt-0.5">{new Date(log.timestamp).toLocaleTimeString('ru-RU')}</span>
            <div className="flex-1 min-w-0">
              <span className={`
                font-bold mr-2
                ${log.level === 'info' ? 'text-blue-400' : ''}
                ${log.level === 'success' ? 'text-green-400' : ''}
                ${log.level === 'warning' ? 'text-yellow-400' : ''}
                ${log.level === 'error' ? 'text-red-400' : ''}
              `}>
                {log.level.toUpperCase()}:
              </span>
              <span className="break-all whitespace-pre-wrap">{log.message}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ETLLogs;