import React, { useState, useEffect } from 'react';
import {
  Search,
  MessageSquare,
  Sparkles,
  Layers,
  Cpu,
  Activity,
  FileText,
  Settings,
  X,
} from 'lucide-react';
import { NavDestination } from './Sidebar';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (tab: NavDestination) => void;
  onTriggerScan: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onNavigate,
  onTriggerScan,
}) => {
  const [query, setQuery] = useState('');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        onClose(); // toggle
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const actions = [
    {
      id: 'chat',
      label: 'Open Chat',
      icon: MessageSquare,
      perform: () => onNavigate('chat'),
    },
    {
      id: 'create',
      label: 'Open Image Studio (Forge)',
      icon: Sparkles,
      perform: () => onNavigate('create'),
    },
    {
      id: 'models',
      label: 'Browse Models',
      icon: Layers,
      perform: () => onNavigate('models'),
    },
    {
      id: 'scan',
      label: 'Trigger Model Scan',
      icon: Layers,
      perform: () => {
        onTriggerScan();
        onNavigate('models');
      },
    },
    {
      id: 'engines',
      label: 'Manage Engines',
      icon: Cpu,
      perform: () => onNavigate('engines'),
    },
    {
      id: 'system',
      label: 'Inspect Hardware & GPU',
      icon: Activity,
      perform: () => onNavigate('system'),
    },
    {
      id: 'logs',
      label: 'View Logs & Diagnostics',
      icon: FileText,
      perform: () => onNavigate('logs'),
    },
    {
      id: 'settings',
      label: 'Open Settings',
      icon: Settings,
      perform: () => onNavigate('settings'),
    },
  ];

  const filtered = actions.filter((a) =>
    a.label.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-start justify-center pt-24">
      <div className="w-full max-w-xl bg-bg-surface border border-bg-border rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-100">
        <div className="p-3 border-b border-bg-border flex items-center gap-3">
          <Search className="w-4 h-4 text-gray-400 ml-1" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command or search..."
            className="w-full bg-transparent border-0 outline-none text-sm text-white placeholder-gray-500 font-sans"
          />
          <button
            onClick={onClose}
            className="p-1 rounded text-gray-400 hover:text-white hover:bg-bg-card"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="max-h-80 overflow-y-auto p-2 space-y-1">
          {filtered.length === 0 ? (
            <div className="py-8 text-center text-xs text-gray-500">
              No matching actions found.
            </div>
          ) : (
            filtered.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    item.perform();
                    onClose();
                  }}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-gray-300 hover:text-white hover:bg-accent-primary/20 text-left transition-colors"
                >
                  <Icon className="w-4 h-4 text-accent-cyan" />
                  <span>{item.label}</span>
                </button>
              );
            })
          )}
        </div>

        <div className="px-4 py-2 border-t border-bg-border/60 bg-bg-card/50 flex justify-between text-[11px] text-gray-500 font-mono">
          <span>Navigate with arrows</span>
          <span>Esc to close</span>
        </div>
      </div>
    </div>
  );
};
