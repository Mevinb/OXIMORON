import React, { useState, useEffect } from 'react';
import {
  Activity,
  Cpu,
  Flame,
  HardDrive,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react';
import { api, SystemSnapshot } from '../../lib/api';

export const SystemPage: React.FC = () => {
  const [system, setSystem] = useState<SystemSnapshot | null>(null);
  const [loading, setLoading] = useState(true);

  const loadSystem = async () => {
    try {
      const data = await api.getSystem();
      setSystem(data);
    } catch (err: any) {
      console.error('Failed to load system snapshot:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSystem();
    const interval = setInterval(loadSystem, 2500);
    return () => clearInterval(interval);
  }, []);

  const gpu = system?.gpus?.[0];

  if (loading) {
    return (
      <div className="p-16 flex items-center justify-center h-[calc(100vh-3.5rem)] text-gray-500 text-sm">
        <RefreshCw className="w-5 h-5 animate-spin mr-2 text-accent-cyan" />
        Inspecting hardware telemetry...
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto overflow-y-auto h-[calc(100vh-3.5rem)] pb-16">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-bg-card p-6 rounded-2xl border border-bg-border shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Activity className="w-5 h-5 text-accent-cyan" />
            Hardware & Resource Telemetry
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            Real-time hardware inspection via direct NVML ctypes and psutil system calls.
          </p>
        </div>

        <button
          onClick={loadSystem}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-bg-surface border border-bg-border text-xs text-gray-300 hover:text-white transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Snapshot</span>
        </button>
      </div>

      {/* Primary Hardware Gauges */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* CPU & Host RAM */}
        <div className="bg-bg-card p-6 rounded-2xl border border-bg-border space-y-5 shadow-sm">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Cpu className="w-4 h-4 text-accent-cyan" /> Host Compute & Memory
          </h2>

          {/* CPU Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-gray-400 font-medium">CPU Utilization</span>
              <span className="font-mono text-white font-semibold">
                {system?.cpu_utilization_pct != null ? `${system.cpu_utilization_pct.toFixed(1)}%` : '--'}
              </span>
            </div>
            <div className="w-full bg-bg-surface h-3 rounded-full overflow-hidden border border-bg-border/80">
              <div
                className="bg-accent-cyan h-full rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, system?.cpu_utilization_pct || 0)}%` }}
              />
            </div>
          </div>

          {/* RAM Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-gray-400 font-medium">System RAM</span>
              <span className="font-mono text-white font-semibold">
                {system
                  ? `${(system.ram_used_bytes / 1e9).toFixed(1)} GB / ${(
                      system.ram_total_bytes / 1e9
                    ).toFixed(1)} GB`
                  : '--'}
              </span>
            </div>
            <div className="w-full bg-bg-surface h-3 rounded-full overflow-hidden border border-bg-border/80">
              <div
                className="bg-accent-primary h-full rounded-full transition-all duration-500"
                style={{
                  width: `${
                    system
                      ? Math.min(100, (system.ram_used_bytes / system.ram_total_bytes) * 100)
                      : 0
                  }%`,
                }}
              />
            </div>
            <div className="flex justify-between text-[11px] font-mono text-gray-500">
              <span>Free: {system ? (system.ram_free_bytes / 1e9).toFixed(1) : 0} GB</span>
              <span>
                {system
                  ? `${((system.ram_used_bytes / system.ram_total_bytes) * 100).toFixed(0)}% used`
                  : ''}
              </span>
            </div>
          </div>
        </div>

        {/* NVIDIA Dedicated GPU */}
        <div className="bg-bg-card p-6 rounded-2xl border border-bg-border space-y-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Flame className="w-4 h-4 text-accent-amber" /> NVIDIA Dedicated GPU
            </h2>
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-mono font-medium ${
                gpu ? 'bg-accent-emerald/20 text-accent-emerald' : 'bg-gray-800 text-gray-400'
              }`}
            >
              {gpu ? 'NVML Active' : 'Not Detected'}
            </span>
          </div>

          {gpu ? (
            <div className="space-y-4">
              <div>
                <div className="text-sm font-bold text-white">{gpu.name}</div>
                <div className="text-xs text-gray-400 font-mono">Device Index: {gpu.index}</div>
              </div>

              {/* VRAM Bar */}
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400 font-medium">VRAM Usage</span>
                  <span className="font-mono text-white font-semibold">
                    {(gpu.used_memory_bytes / 1e6).toFixed(0)} MB /{' '}
                    {(gpu.total_memory_bytes / 1e6).toFixed(0)} MB
                  </span>
                </div>
                <div className="w-full bg-bg-surface h-3 rounded-full overflow-hidden border border-bg-border/80">
                  <div
                    className="bg-accent-amber h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.min(
                        100,
                        (gpu.used_memory_bytes / gpu.total_memory_bytes) * 100
                      )}%`,
                    }}
                  />
                </div>
              </div>

              {/* Sub metrics grid */}
              <div className="grid grid-cols-3 gap-3 pt-2 text-center">
                <div className="bg-bg-surface/80 p-3 rounded-xl border border-bg-border">
                  <div className="text-xs text-gray-400">Temperature</div>
                  <div className="text-base font-bold text-accent-emerald font-mono mt-1">
                    {gpu.temperature_c != null ? `${gpu.temperature_c}°C` : '--'}
                  </div>
                </div>
                <div className="bg-bg-surface/80 p-3 rounded-xl border border-bg-border">
                  <div className="text-xs text-gray-400">Power Draw</div>
                  <div className="text-base font-bold text-accent-cyan font-mono mt-1">
                    {gpu.power_draw_w != null ? `${gpu.power_draw_w.toFixed(0)} W` : '--'}
                  </div>
                </div>
                <div className="bg-bg-surface/80 p-3 rounded-xl border border-bg-border">
                  <div className="text-xs text-gray-400">Utilization</div>
                  <div className="text-base font-bold text-accent-primary font-mono mt-1">
                    {gpu.utilization_pct != null ? `${gpu.utilization_pct}%` : '0%'}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-gray-500 font-mono">
              NVIDIA GPU not accessible via NVML on this session.
            </div>
          )}
        </div>
      </div>

      {/* Storage & Disks */}
      <div className="bg-bg-card p-6 rounded-2xl border border-bg-border space-y-4 shadow-sm">
        <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
          <HardDrive className="w-4 h-4 text-accent-cyan" /> Mounted Storage Disks
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {system?.disks &&
            Object.entries(system.disks).map(([mount, disk]) => {
              const usedGb = (disk.used_bytes / 1e9).toFixed(1);
              const totalGb = (disk.total_bytes / 1e9).toFixed(1);
              const pct = Math.min(100, (disk.used_bytes / disk.total_bytes) * 100);

              return (
                <div
                  key={mount}
                  className="bg-bg-surface/80 p-4 rounded-xl border border-bg-border space-y-2.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-white truncate max-w-[200px]">
                      {mount}
                    </span>
                    <span className="text-xs font-mono text-gray-400">{pct.toFixed(0)}%</span>
                  </div>

                  <div className="w-full bg-bg-card h-2 rounded-full overflow-hidden border border-bg-border/60">
                    <div
                      className="bg-accent-cyan h-full rounded-full transition-all duration-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>

                  <div className="text-[11px] font-mono text-gray-400 flex justify-between">
                    <span>{usedGb} GB used</span>
                    <span>{totalGb} GB total</span>
                  </div>
                </div>
              );
            })}
        </div>
      </div>

      {/* Security & Isolation Status */}
      <div className="bg-bg-card p-6 rounded-2xl border border-bg-border flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-accent-emerald/15 border border-accent-emerald/30 flex items-center justify-center text-accent-emerald">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold text-white text-sm">Offline Loopback Isolation</h3>
            <p className="text-xs text-gray-400">
              OXIMORON binds strictly to 127.0.0.1. Model parsing uses safe AST/headers without pickle or torch.load execution.
            </p>
          </div>
        </div>

        <span className="text-xs px-3 py-1 rounded-full bg-accent-emerald/20 text-accent-emerald font-mono font-medium border border-accent-emerald/30">
          Enforced
        </span>
      </div>
    </div>
  );
};
