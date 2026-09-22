import React, { useState, useEffect, useRef } from 'react';
import {
  Search,
  RefreshCw,
  ArrowDownCircle,
  Copy,
  Check,
} from 'lucide-react';
import { api, LogItem } from '../../lib/api';

export const LogsPage: React.FC = () => {
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [levelFilter, setLevelFilter] = useState<string>('ALL');
  const [search, setSearch] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const [copied, setCopied] = useState(false);
  const logEndRef = useRef<HTMLDivElement>(null);

  const loadLogs = async () => {
    try {
      const res = await api.getLogs(levelFilter, 200);
      if (res && res.entries) {
        setLogs(res.entries);
      }
    } catch (err: any) {
      console.error('Failed to load logs:', err);
    }
  };

  useEffect(() => {
    loadLogs();
    const interval = setInterval(loadLogs, 2500);
    return () => clearInterval(interval);
  }, [levelFilter]);

  useEffect(() => {
    if (autoScroll) {
      logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const levels = ['ALL', 'INFO', 'WARNING', 'ERROR'];

  const filteredLogs = logs.filter((l) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      l.message.toLowerCase().includes(q) ||
      l.component.toLowerCase().includes(q) ||
      l.level.toLowerCase().includes(q)
    );
  });

  const handleCopyAll = () => {
    const raw = filteredLogs
      .map((l) => `[${l.timestamp}] [${l.level}] [${l.component}] ${l.message}`)
      .join('\n');
    navigator.clipboard.writeText(raw);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getLevelColor = (level: string) => {
    switch (level.toUpperCase()) {
      case 'ERROR':
        return 'text-accent-rose bg-accent-rose/10 border-accent-rose/30';
      case 'WARNING':
      case 'WARN':
        return 'text-accent-amber bg-accent-amber/10 border-accent-amber/30';
      case 'INFO':
        return 'text-accent-cyan bg-accent-cyan/10 border-accent-cyan/30';
      default:
        return 'text-gray-400 bg-gray-800 border-gray-700';
    }
  };

  return (
    <div className="p-6 space-y-4 max-w-7xl mx-auto h-[calc(100vh-3.5rem)] flex flex-col justify-between overflow-hidden">
      {/* Top Filter Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-bg-card p-4 rounded-2xl border border-bg-border shadow-sm">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search logs..."
              className="w-full bg-bg-surface border border-bg-border rounded-xl pl-9 pr-3 py-1.5 text-xs text-white placeholder-gray-500 outline-none focus:border-accent-primary font-mono"
            />
          </div>

          <div className="flex items-center gap-1 bg-bg-surface p-1 rounded-xl border border-bg-border">
            {levels.map((lvl) => (
              <button
                key={lvl}
                onClick={() => setLevelFilter(lvl)}
                className={`px-3 py-1 rounded-lg text-xs font-mono transition font-medium ${
                  levelFilter === lvl
                    ? 'bg-accent-primary text-white shadow-sm'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {lvl}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-medium transition ${
              autoScroll
                ? 'bg-accent-emerald/15 border-accent-emerald/30 text-accent-emerald'
                : 'bg-bg-surface border-bg-border text-gray-400 hover:text-white'
            }`}
          >
            <ArrowDownCircle className="w-3.5 h-3.5" />
            <span>Auto-Scroll: {autoScroll ? 'ON' : 'OFF'}</span>
          </button>

          <button
            onClick={handleCopyAll}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-bg-surface border border-bg-border text-xs text-gray-300 hover:text-white transition"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-accent-emerald" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>

          <button
            onClick={loadLogs}
            className="p-2 rounded-xl bg-bg-surface border border-bg-border text-gray-400 hover:text-white transition"
            title="Refresh logs"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Terminal View Area */}
      <div className="flex-1 bg-bg-surface rounded-2xl border border-bg-border p-4 font-mono text-xs overflow-y-auto space-y-1 shadow-inner select-text">
        {filteredLogs.length === 0 ? (
          <div className="h-full flex items-center justify-center text-gray-500">
            No log entries matching criteria.
          </div>
        ) : (
          filteredLogs.map((l) => (
            <div
              key={l.id}
              className="flex items-start gap-3 py-1 px-2 rounded hover:bg-bg-card/60 transition group font-mono"
            >
              <span className="text-gray-500 shrink-0 select-none">
                {new Date(l.timestamp).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                })}
              </span>

              <span
                className={`px-1.5 py-0.2 rounded text-[10px] uppercase font-bold border shrink-0 ${getLevelColor(
                  l.level
                )}`}
              >
                {l.level}
              </span>

              <span className="text-accent-primary/80 shrink-0">[{l.component}]</span>

              <span className="text-gray-200 break-all group-hover:text-white">
                {l.message}
              </span>
            </div>
          ))
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );
};
