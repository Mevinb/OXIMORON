import React from 'react';
import {
  Home,
  MessageSquare,
  Sparkles,
  Layers,
  Cpu,
  Activity,
  FileText,
  Settings,
  CircleDot,
} from 'lucide-react';
import { StatusSummary } from '../lib/api';

export type NavDestination =
  | 'home'
  | 'chat'
  | 'create'
  | 'models'
  | 'engines'
  | 'system'
  | 'logs'
  | 'settings';

interface SidebarProps {
  currentTab: NavDestination;
  onSelectTab: (tab: NavDestination) => void;
  status: StatusSummary | null;
  connected: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  status,
  connected,
}) => {
  const navItems = [
    { id: 'home', label: 'Home', icon: Home },
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'create', label: 'Create', icon: Sparkles },
    { id: 'models', label: 'Models', icon: Layers },
    { id: 'engines', label: 'Engines', icon: Cpu },
    { id: 'system', label: 'System', icon: Activity },
    { id: 'logs', label: 'Logs', icon: FileText },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-bg-surface border-r border-bg-border flex flex-col justify-between select-none h-screen">
      {/* Brand header */}
      <div>
        <div className="p-5 flex items-center gap-3 border-b border-bg-border/60">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-accent-primary to-accent-cyan p-[2px] shadow-lg shadow-accent-primary/20">
            <div className="w-full h-full bg-bg-surface rounded-md flex items-center justify-center font-bold text-white tracking-wider text-sm">
              <span className="text-accent-cyan">O</span>
              <span className="text-accent-primary">X</span>
            </div>
          </div>
          <div>
            <h1 className="font-bold text-base tracking-wide text-white flex items-center gap-1.5">
              OXIMORON
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-accent-primary/20 text-accent-primary border border-accent-primary/30">
                v0.1
              </span>
            </h1>
            <p className="text-xs text-gray-400 font-mono">Local AI Center</p>
          </div>
        </div>

        {/* Navigation list */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id as NavDestination)}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-accent-primary/15 text-white font-semibold border border-accent-primary/30 shadow-sm'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-bg-card'
                }`}
              >
                <Icon
                  className={`w-4 h-4 ${
                    isActive ? 'text-accent-cyan' : 'text-gray-400'
                  }`}
                />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* System status pill */}
      <div className="p-4 border-t border-bg-border/60 bg-bg-card/40 m-3 rounded-xl border border-bg-border">
        <div className="flex items-center justify-between text-xs mb-2">
          <span className="text-gray-400 flex items-center gap-1.5">
            <CircleDot
              className={`w-3 h-3 ${
                connected ? 'text-accent-emerald animate-pulse' : 'text-accent-rose'
              }`}
            />
            {connected ? 'Supervisor Online' : 'Connecting...'}
          </span>
          {status?.gpu_available && (
            <span className="px-1.5 py-0.5 text-[10px] rounded bg-accent-emerald/20 text-accent-emerald font-mono">
              RTX 4050
            </span>
          )}
        </div>
        {status && (
          <div className="space-y-1.5 text-[11px] font-mono text-gray-400">
            <div className="flex justify-between">
              <span>RAM</span>
              <span className="text-gray-200">
                {status.ram_used_gb} / {status.ram_total_gb} GB
              </span>
            </div>
            <div className="w-full bg-bg-border h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-accent-primary h-full transition-all duration-500 rounded-full"
                style={{
                  width: `${Math.min(
                    100,
                    (status.ram_used_gb / status.ram_total_gb) * 100
                  )}%`,
                }}
              />
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
