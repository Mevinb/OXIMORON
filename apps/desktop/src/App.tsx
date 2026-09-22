import React, { useState, useEffect } from 'react';
import { Sidebar, NavDestination } from './components/Sidebar';
import { Header } from './components/Header';
import { CommandPalette } from './components/CommandPalette';
import { HomePage } from './features/home/HomePage';
import { ChatPage } from './features/chat/ChatPage';
import { CreatePage } from './features/create/CreatePage';
import { ModelsPage } from './features/models/ModelsPage';
import { EnginesPage } from './features/engines/EnginesPage';
import { SystemPage } from './features/system/SystemPage';
import { LogsPage } from './features/logs/LogsPage';
import { SettingsPage } from './features/settings/SettingsPage';
import { api, StatusSummary } from './lib/api';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<NavDestination>('home');
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [status, setStatus] = useState<StatusSummary | null>(null);
  const [connected, setConnected] = useState(false);
  const [apiToken, setApiToken] = useState<string>(() => {
    return localStorage.getItem('oximoron_token') || '';
  });

  useEffect(() => {
    if (apiToken) {
      api.setToken(apiToken);
    }
  }, [apiToken]);

  const handleUpdateToken = (token: string) => {
    setApiToken(token);
    localStorage.setItem('oximoron_token', token);
    api.setToken(token);
  };

  const pollStatus = async () => {
    try {
      const res = await api.getStatus();
      setStatus(res);
      setConnected(true);
    } catch {
      setConnected(false);
    }
  };

  useEffect(() => {
    pollStatus();
    const interval = setInterval(pollStatus, 3000);
    return () => clearInterval(interval);
  }, [apiToken]);

  const handleTriggerScan = async () => {
    try {
      await api.scanModels();
    } catch (err: any) {
      console.error('Scan failed:', err);
    }
  };

  const renderActivePage = () => {
    switch (currentTab) {
      case 'home':
        return <HomePage onNavigate={setCurrentTab} onTriggerScan={handleTriggerScan} />;
      case 'chat':
        return <ChatPage />;
      case 'create':
        return <CreatePage />;
      case 'models':
        return <ModelsPage onNavigate={setCurrentTab} />;
      case 'engines':
        return <EnginesPage />;
      case 'system':
        return <SystemPage />;
      case 'logs':
        return <LogsPage />;
      case 'settings':
        return (
          <SettingsPage apiToken={apiToken} onUpdateToken={handleUpdateToken} />
        );
      default:
        return <HomePage onNavigate={setCurrentTab} onTriggerScan={handleTriggerScan} />;
    }
  };

  return (
    <div className="flex h-screen w-screen bg-bg-main text-slate-100 overflow-hidden font-sans">
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        status={status}
        connected={connected}
      />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Header
          currentTab={currentTab}
          onOpenCommandPalette={() => setCommandPaletteOpen(true)}
          apiToken={apiToken}
        />

        <main className="flex-1 overflow-hidden bg-bg-main relative">
          {renderActivePage()}
        </main>
      </div>

      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        onNavigate={setCurrentTab}
        onTriggerScan={handleTriggerScan}
      />
    </div>
  );
};
