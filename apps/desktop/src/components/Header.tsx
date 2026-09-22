import React from 'react';
import { Search, ShieldCheck } from 'lucide-react';
import { NavDestination } from './Sidebar';

interface HeaderProps {
  currentTab: NavDestination;
  onOpenCommandPalette: () => void;
  apiToken: string;
}

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  onOpenCommandPalette,
  apiToken,
}) => {
  const titles: Record<NavDestination, string> = {
    home: 'Control Center',
    chat: 'Local Chat Studio',
    create: 'Image Studio (Forge)',
    models: 'Model Library & Registry',
    engines: 'Inference Engines',
    system: 'Hardware & Telemetry',
    logs: 'Logs & Diagnostics',
    settings: 'Configuration & Settings',
  };

  return (
    <header className="h-14 border-b border-bg-border bg-bg-surface/50 backdrop-blur-md px-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <h2 className="font-semibold text-base text-white tracking-wide">
          {titles[currentTab]}
        </h2>
      </div>

      <div className="flex items-center gap-4">
        {/* Command palette search bar trigger */}
        <button
          onClick={onOpenCommandPalette}
          className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-bg-card border border-bg-border text-xs text-gray-400 hover:text-gray-200 hover:border-gray-600 transition-all shadow-sm"
        >
          <Search className="w-3.5 h-3.5 text-gray-400" />
          <span>Quick actions & search</span>
          <kbd className="ml-2 font-mono text-[10px] bg-bg-surface px-1.5 py-0.5 rounded border border-bg-border text-gray-400">
            Ctrl+K
          </kbd>
        </button>

        {/* Security / Token pill */}
        <div className="flex items-center gap-2 text-xs font-mono text-gray-400 bg-bg-card/70 px-2.5 py-1 rounded-md border border-bg-border">
          <ShieldCheck className={`w-3.5 h-3.5 ${apiToken ? 'text-accent-emerald' : 'text-accent-amber'}`} />
          <span>Loopback: 127.0.0.1</span>
          <span className="text-[10px] text-gray-500">
            {apiToken ? `(Token: ${apiToken.slice(0, 4)}...)` : '(No Token)'}
          </span>
        </div>
      </div>
    </header>
  );
};
