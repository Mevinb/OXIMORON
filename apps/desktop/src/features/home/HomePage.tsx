import React, { useState, useEffect } from 'react';
import {
  Activity,
  Cpu,
  Layers,
  MessageSquare,
  Sparkles,
  RefreshCw,
  CheckCircle2,
  Play,
  Square,
  Flame,
  ArrowUpRight,
} from 'lucide-react';
import {
  api,
  StatusSummary,
  SystemSnapshot,
  EngineItem,
  ModelItem,
} from '../../lib/api';
import { NavDestination } from '../../components/Sidebar';

interface HomePageProps {
  onNavigate: (tab: NavDestination) => void;
  onTriggerScan: () => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onNavigate, onTriggerScan }) => {
  const [status, setStatus] = useState<StatusSummary | null>(null);
  const [system, setSystem] = useState<SystemSnapshot | null>(null);
  const [engines, setEngines] = useState<EngineItem[]>([]);
  const [models, setModels] = useState<ModelItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = async () => {
    try {
      const [statusRes, sysRes, enginesRes, modelsRes] = await Promise.all([
        api.getStatus().catch(() => null),
        api.getSystem().catch(() => null),
        api.getEngines().catch(() => []),
        api.getModels().catch(() => []),
      ]);
      if (statusRes) setStatus(statusRes);
      if (sysRes) setSystem(sysRes);
      if (enginesRes) setEngines(enginesRes);
      if (modelsRes) setModels(modelsRes);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleToggleEngine = async (engine: EngineItem) => {
    try {
      if (engine.observed_state === 'RUNNING') {
        await api.stopEngine(engine.id);
      } else {
        await api.startEngine(engine.id);
      }
      await loadData();
    } catch (err: any) {
      alert(`Engine action failed: ${err.message}`);
    }
  };

  const gpu = system?.gpus?.[0];

  if (loading) {
    return (
      <div className="p-16 flex items-center justify-center h-[calc(100vh-3.5rem)] text-gray-500 text-sm">
        <RefreshCw className="w-5 h-5 animate-spin mr-2 text-accent-cyan" />
        Connecting to local supervisor...
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto overflow-y-auto h-[calc(100vh-3.5rem)] pb-16">
      {/* Top Banner & Quick Refresh */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-bg-card via-bg-surface to-bg-card p-6 rounded-2xl border border-bg-border shadow-md">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-3">
            Welcome to OXIMORON
            <span className="text-xs px-2.5 py-1 rounded-full bg-accent-primary/20 text-accent-cyan border border-accent-primary/30 font-mono">
              Local First
            </span>
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Private local desktop AI orchestration center. All inferences execute on loopback hardware.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setRefreshing(true);
              loadData();
            }}
            disabled={refreshing}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-bg-surface border border-bg-border text-xs text-gray-300 hover:text-white hover:border-gray-600 transition shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-accent-cyan' : ''}`} />
            <span>Sync</span>
          </button>
          <button
            onClick={onTriggerScan}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-accent-primary hover:bg-accent-primary/90 text-white text-xs font-semibold shadow-lg shadow-accent-primary/25 transition"
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Scan Models</span>
          </button>
        </div>
      </div>

      {/* Hardware Snapshot Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* CPU */}
        <div className="bg-bg-card p-4 rounded-xl border border-bg-border flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-gray-400">
            <span className="flex items-center gap-2 font-medium">
              <Cpu className="w-4 h-4 text-accent-cyan" /> CPU Utilization
            </span>
            <span className="font-mono text-white text-sm font-semibold">
              {system?.cpu_utilization_pct != null ? `${system.cpu_utilization_pct.toFixed(1)}%` : '--'}
            </span>
          </div>
          <div className="mt-4">
            <div className="w-full bg-bg-surface h-2 rounded-full overflow-hidden border border-bg-border/60">
              <div
                className="bg-accent-cyan h-full rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, system?.cpu_utilization_pct || 0)}%` }}
              />
            </div>
          </div>
        </div>

        {/* RAM */}
        <div className="bg-bg-card p-4 rounded-xl border border-bg-border flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-gray-400">
            <span className="flex items-center gap-2 font-medium">
              <Activity className="w-4 h-4 text-accent-primary" /> System RAM
            </span>
            <span className="font-mono text-white text-sm font-semibold">
              {status ? `${status.ram_used_gb} / ${status.ram_total_gb} GB` : '--'}
            </span>
          </div>
          <div className="mt-4">
            <div className="w-full bg-bg-surface h-2 rounded-full overflow-hidden border border-bg-border/60">
              <div
                className="bg-accent-primary h-full rounded-full transition-all duration-500"
                style={{
                  width: `${
                    status ? Math.min(100, (status.ram_used_gb / status.ram_total_gb) * 100) : 0
                  }%`,
                }}
              />
            </div>
          </div>
        </div>

        {/* GPU VRAM */}
        <div className="bg-bg-card p-4 rounded-xl border border-bg-border flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-gray-400">
            <span className="flex items-center gap-2 font-medium">
              <Flame className="w-4 h-4 text-accent-amber" /> GPU VRAM
            </span>
            <span className="font-mono text-white text-sm font-semibold">
              {gpu ? `${(gpu.used_memory_bytes / 1e9).toFixed(1)} / ${(gpu.total_memory_bytes / 1e9).toFixed(1)} GB` : 'N/A'}
            </span>
          </div>
          <div className="mt-4">
            <div className="w-full bg-bg-surface h-2 rounded-full overflow-hidden border border-bg-border/60">
              <div
                className="bg-accent-amber h-full rounded-full transition-all duration-500"
                style={{
                  width: `${
                    gpu ? Math.min(100, (gpu.used_memory_bytes / gpu.total_memory_bytes) * 100) : 0
                  }%`,
                }}
              />
            </div>
          </div>
        </div>

        {/* GPU Temp & Power */}
        <div className="bg-bg-card p-4 rounded-xl border border-bg-border flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-gray-400">
            <span className="flex items-center gap-2 font-medium">
              <CheckCircle2 className="w-4 h-4 text-accent-emerald" /> RTX 4050 Stats
            </span>
            <span className="font-mono text-accent-emerald text-sm font-semibold">
              {gpu?.temperature_c != null ? `${gpu.temperature_c}°C` : 'Offline'}
            </span>
          </div>
          <div className="mt-3 flex justify-between items-center text-xs font-mono text-gray-400">
            <span>Power: {gpu?.power_draw_w != null ? `${gpu.power_draw_w.toFixed(0)} W` : '--'}</span>
            <span>Util: {gpu?.utilization_pct != null ? `${gpu.utilization_pct}%` : '0%'}</span>
          </div>
        </div>
      </div>

      {/* Quick Launch Action Tiles */}
      <div>
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
          Quick Launch Studios
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            onClick={() => onNavigate('chat')}
            className="group p-5 rounded-xl bg-bg-card border border-bg-border hover:border-accent-primary/60 hover:bg-bg-cardHover transition text-left flex flex-col justify-between shadow-sm relative overflow-hidden"
          >
            <div className="flex items-start justify-between">
              <div className="w-10 h-10 rounded-lg bg-accent-primary/15 border border-accent-primary/30 flex items-center justify-center text-accent-primary group-hover:scale-110 transition">
                <MessageSquare className="w-5 h-5" />
              </div>
              <ArrowUpRight className="w-4 h-4 text-gray-500 group-hover:text-accent-primary transition" />
            </div>
            <div className="mt-4">
              <h3 className="font-semibold text-white text-base">Chat Studio</h3>
              <p className="text-xs text-gray-400 mt-1">
                Stream conversational inference via local llama.cpp GGUF models.
              </p>
            </div>
          </button>

          <button
            onClick={() => onNavigate('create')}
            className="group p-5 rounded-xl bg-bg-card border border-bg-border hover:border-accent-cyan/60 hover:bg-bg-cardHover transition text-left flex flex-col justify-between shadow-sm relative overflow-hidden"
          >
            <div className="flex items-start justify-between">
              <div className="w-10 h-10 rounded-lg bg-accent-cyan/15 border border-accent-cyan/30 flex items-center justify-center text-accent-cyan group-hover:scale-110 transition">
                <Sparkles className="w-5 h-5" />
              </div>
              <ArrowUpRight className="w-4 h-4 text-gray-500 group-hover:text-accent-cyan transition" />
            </div>
            <div className="mt-4">
              <h3 className="font-semibold text-white text-base">Image Studio</h3>
              <p className="text-xs text-gray-400 mt-1">
                Synthesize images locally using Forge SDXL / FLUX pipelines.
              </p>
            </div>
          </button>

          <button
            onClick={() => onNavigate('models')}
            className="group p-5 rounded-xl bg-bg-card border border-bg-border hover:border-accent-emerald/60 hover:bg-bg-cardHover transition text-left flex flex-col justify-between shadow-sm relative overflow-hidden"
          >
            <div className="flex items-start justify-between">
              <div className="w-10 h-10 rounded-lg bg-accent-emerald/15 border border-accent-emerald/30 flex items-center justify-center text-accent-emerald group-hover:scale-110 transition">
                <Layers className="w-5 h-5" />
              </div>
              <ArrowUpRight className="w-4 h-4 text-gray-500 group-hover:text-accent-emerald transition" />
            </div>
            <div className="mt-4">
              <h3 className="font-semibold text-white text-base">Model Registry</h3>
              <p className="text-xs text-gray-400 mt-1">
                Manage {models.length} safely scanned GGUF and Safetensors checkpoints.
              </p>
            </div>
          </button>
        </div>
      </div>

      {/* Engine Status Cards */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
            Inference Engines
          </h2>
          <button
            onClick={() => onNavigate('engines')}
            className="text-xs text-accent-primary hover:text-accent-cyan transition font-medium flex items-center gap-1"
          >
            Manage all <ArrowUpRight className="w-3 h-3" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {engines.map((engine) => {
            const isRunning = engine.observed_state === 'RUNNING';
            return (
              <div
                key={engine.id}
                className="bg-bg-card p-4 rounded-xl border border-bg-border flex flex-col justify-between gap-3 shadow-sm"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white text-sm">
                    {engine.display_name}
                  </span>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-medium ${
                      isRunning
                        ? 'bg-accent-emerald/20 text-accent-emerald border border-accent-emerald/30'
                        : 'bg-gray-800 text-gray-400 border border-gray-700'
                    }`}
                  >
                    {engine.observed_state}
                  </span>
                </div>
                <div className="text-xs text-gray-400 font-mono truncate">
                  Endpoint: {engine.endpoint || 'Not bound'}
                </div>
                <div className="flex items-center justify-between pt-2 border-t border-bg-border/60">
                  <span className="text-[11px] text-gray-500 font-mono">
                    {engine.capabilities.tasks.join(', ')}
                  </span>
                  <button
                    onClick={() => handleToggleEngine(engine)}
                    className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs font-medium transition ${
                      isRunning
                        ? 'bg-accent-rose/20 text-accent-rose hover:bg-accent-rose/30 border border-accent-rose/30'
                        : 'bg-accent-primary/20 text-accent-primary hover:bg-accent-primary/30 border border-accent-primary/30'
                    }`}
                  >
                    {isRunning ? <Square className="w-3 h-3" /> : <Play className="w-3 h-3" />}
                    <span>{isRunning ? 'Stop' : 'Start'}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Featured Models Preview */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
            Discovered Models ({models.length})
          </h2>
          <button
            onClick={() => onNavigate('models')}
            className="text-xs text-accent-primary hover:text-accent-cyan transition font-medium flex items-center gap-1"
          >
            View all models <ArrowUpRight className="w-3 h-3" />
          </button>
        </div>

        <div className="bg-bg-card rounded-xl border border-bg-border overflow-hidden shadow-sm">
          {models.length === 0 ? (
            <div className="p-8 text-center text-sm text-gray-500">
              No models discovered yet. Click "Scan Models" to index local checkpoints.
            </div>
          ) : (
            <div className="divide-y divide-bg-border">
              {models.slice(0, 5).map((model) => (
                <div
                  key={model.id}
                  className="p-3.5 px-5 flex items-center justify-between hover:bg-bg-cardHover transition"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xs px-2 py-0.5 rounded font-mono font-semibold bg-bg-surface border border-bg-border text-accent-cyan uppercase">
                      {model.format}
                    </span>
                    <div>
                      <div className="text-sm font-medium text-white">{model.name}</div>
                      <div className="text-xs text-gray-400 font-mono">
                        {model.role} • {model.quantization || 'FP16/Full'} •{' '}
                        {model.locations[0]
                          ? `${(model.locations[0].byte_size / 1e9).toFixed(2)} GB`
                          : ''}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => onNavigate(model.role === 'llm' ? 'chat' : 'create')}
                    className="text-xs px-3 py-1 rounded bg-bg-surface hover:bg-bg-border text-gray-300 hover:text-white transition"
                  >
                    Open Studio
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
