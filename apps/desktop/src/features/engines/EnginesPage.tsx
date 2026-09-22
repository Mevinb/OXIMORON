import React, { useState, useEffect } from 'react';
import {
  Cpu,
  Play,
  Square,
  RefreshCw,
  Search,
} from 'lucide-react';
import { api, EngineItem } from '../../lib/api';

export const EnginesPage: React.FC = () => {
  const [engines, setEngines] = useState<EngineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [discovering, setDiscovering] = useState(false);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  const loadEngines = async () => {
    try {
      const data = await api.getEngines();
      setEngines(data);
    } catch (err: any) {
      console.error('Failed to load engines:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEngines();
    const interval = setInterval(loadEngines, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleDiscover = async () => {
    setDiscovering(true);
    try {
      const discovered = await api.discoverEngines();
      setEngines(discovered);
    } catch (err: any) {
      alert(`Discovery failed: ${err.message}`);
    } finally {
      setDiscovering(false);
    }
  };

  const handleToggleEngine = async (engine: EngineItem) => {
    setActionInProgress(engine.id);
    try {
      if (engine.observed_state === 'RUNNING') {
        await api.stopEngine(engine.id);
      } else {
        await api.startEngine(engine.id);
      }
      await loadEngines();
    } catch (err: any) {
      alert(`Engine action error: ${err.message}`);
    } finally {
      setActionInProgress(null);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto overflow-y-auto h-[calc(100vh-3.5rem)] pb-16">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-bg-card p-6 rounded-2xl border border-bg-border shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Cpu className="w-5 h-5 text-accent-cyan" />
            Inference Engine Supervisors
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            Manage local isolated engine runtimes. Processes are spawned with detached process groups and supervised without interfering with OXIMORON core.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadEngines}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-bg-surface border border-bg-border text-xs text-gray-300 hover:text-white transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
          <button
            onClick={handleDiscover}
            disabled={discovering}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-primary hover:bg-accent-primary/90 disabled:opacity-50 text-white font-semibold text-xs shadow-lg shadow-accent-primary/20 transition"
          >
            <Search className={`w-3.5 h-3.5 ${discovering ? 'animate-spin' : ''}`} />
            <span>{discovering ? 'Probing System...' : 'Auto-Discover Engines'}</span>
          </button>
        </div>
      </div>

      {/* Engine Cards */}
      {loading ? (
        <div className="p-16 text-center text-sm text-gray-500">Loading engine instances...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {engines.map((engine) => {
            const isRunning = engine.observed_state === 'RUNNING';
            const isActing = actionInProgress === engine.id;

          return (
            <div
              key={engine.id}
              className="bg-bg-card border border-bg-border hover:border-gray-600 rounded-2xl p-6 flex flex-col justify-between gap-5 transition shadow-sm"
            >
              <div className="space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-base font-bold text-white tracking-wide">
                      {engine.display_name}
                    </h3>
                    <span className="text-[11px] font-mono text-accent-cyan">
                      adapter: {engine.adapter_key}
                    </span>
                  </div>

                  <span
                    className={`text-xs px-2.5 py-1 rounded-full font-mono font-semibold ${
                      isRunning
                        ? 'bg-accent-emerald/20 text-accent-emerald border border-accent-emerald/30'
                        : 'bg-gray-800 text-gray-400 border border-gray-700'
                    }`}
                  >
                    {engine.observed_state}
                  </span>
                </div>

                {/* Details list */}
                <div className="space-y-2 bg-bg-surface/70 rounded-xl p-3 border border-bg-border text-xs font-mono">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Endpoint</span>
                    <span className="text-gray-300 truncate max-w-[160px]">
                      {engine.endpoint || 'Offline (Not bound)'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Tasks</span>
                    <span className="text-accent-primary truncate max-w-[160px]">
                      {engine.capabilities.tasks.join(', ')}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Streaming</span>
                    <span className={engine.capabilities.streaming ? 'text-accent-emerald' : 'text-gray-500'}>
                      {engine.capabilities.streaming ? 'Supported' : 'No'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Config Key</span>
                    <span className="text-gray-400">{engine.config_key}</span>
                  </div>
                </div>
              </div>

              {/* Action Button */}
              <div className="pt-3 border-t border-bg-border/60">
                <button
                  onClick={() => handleToggleEngine(engine)}
                  disabled={isActing}
                  className={`w-full py-2.5 rounded-xl font-semibold text-xs flex items-center justify-center gap-2 transition shadow-md ${
                    isRunning
                      ? 'bg-accent-rose/20 text-accent-rose hover:bg-accent-rose/30 border border-accent-rose/30'
                      : 'bg-accent-primary hover:bg-accent-primary/90 text-white shadow-accent-primary/20'
                  }`}
                >
                  {isActing ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Processing...</span>
                    </>
                  ) : isRunning ? (
                    <>
                      <Square className="w-4 h-4" />
                      <span>Stop Engine</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" />
                      <span>Start Engine</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>
      )}
    </div>
  );
};
