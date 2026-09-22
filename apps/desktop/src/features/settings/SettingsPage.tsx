import React, { useState, useEffect } from 'react';
import {
  Settings,
  Shield,
  Key,
  Folder,
  Server,
  Save,
  CheckCircle2,
  Eye,
  EyeOff,
} from 'lucide-react';
import { api } from '../../lib/api';

interface SettingsPageProps {
  apiToken: string;
  onUpdateToken: (token: string) => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({
  apiToken,
  onUpdateToken,
}) => {
  const [tokenInput, setTokenInput] = useState(apiToken);
  const [showToken, setShowToken] = useState(false);
  const [host, setHost] = useState('127.0.0.1');
  const [port, setPort] = useState('8420');
  const [modelsPath, setModelsPath] = useState('/home/mevlec/Data');
  const [outputPath, setOutputPath] = useState('~/OXIMORON/generations');
  const [llamaPath, setLlamaPath] = useState('/home/mevlec/llama.cpp/build/bin/llama-server');
  const [forgePath, setForgePath] = useState('/home/mevlec/Data/forge/stable-diffusion-webui-forge');
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setTokenInput(apiToken);
  }, [apiToken]);

  const loadBackendSettings = async () => {
    try {
      const data = await api.getSettings();
      if (data) {
        if (data.server?.host) setHost(data.server.host);
        if (data.server?.port) setPort(String(data.server.port));
        if (data.storage?.model_directories?.[0]) {
          setModelsPath(data.storage.model_directories[0]);
        }
        if (data.storage?.output_directory) {
          setOutputPath(data.storage.output_directory);
        }
        if (data.engines?.llamacpp?.executable_path) {
          setLlamaPath(data.engines.llamacpp.executable_path);
        }
        if (data.engines?.forge?.working_directory) {
          setForgePath(data.engines.forge.working_directory);
        }
      }
    } catch (err: any) {
      console.error('Failed to load settings:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBackendSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (tokenInput.trim() !== apiToken) {
      onUpdateToken(tokenInput.trim());
      api.setToken(tokenInput.trim());
    }

    try {
      await api.saveSettings({
        server: {
          host,
          port: parseInt(port, 10) || 8420,
        },
        storage: {
          model_directories: [modelsPath],
          output_directory: outputPath,
        },
        engines: {
          llamacpp: { executable_path: llamaPath },
          forge: { working_directory: forgePath },
        },
      });
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: any) {
      alert(`Failed to save settings: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="p-16 flex items-center justify-center h-[calc(100vh-3.5rem)] text-gray-500 text-sm">
        Loading configuration...
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto overflow-y-auto h-[calc(100vh-3.5rem)] pb-16">
      {/* Top Banner */}
      <div className="bg-bg-card p-6 rounded-2xl border border-bg-border flex items-center justify-between shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Settings className="w-5 h-5 text-accent-cyan" />
            System Configuration
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            Configure supervisor loopback endpoints, offline storage paths, and engine paths.
          </p>
        </div>

        {savedSuccess && (
          <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-accent-emerald/20 text-accent-emerald text-xs font-medium border border-accent-emerald/30 animate-in fade-in">
            <CheckCircle2 className="w-4 h-4" />
            <span>Settings Saved!</span>
          </div>
        )}
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Security & Authentication */}
        <div className="bg-bg-card p-6 rounded-2xl border border-bg-border space-y-4 shadow-sm">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Shield className="w-4 h-4 text-accent-cyan" /> API Authentication & Token
          </h2>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-gray-300 flex items-center gap-1.5">
              <Key className="w-3.5 h-3.5 text-accent-primary" /> Supervisor Bearer Token
            </label>
            <div className="relative">
              <input
                type={showToken ? 'text' : 'password'}
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                placeholder="Enter supervisor API bearer token..."
                className="w-full bg-bg-surface border border-bg-border rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-gray-500 font-mono outline-none focus:border-accent-primary pr-10"
              />
              <button
                type="button"
                onClick={() => setShowToken(!showToken)}
                className="absolute right-3 top-2.5 text-gray-400 hover:text-white"
              >
                {showToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-[11px] text-gray-500">
              Tokens are stored securely in <code>~/.oximoron/credentials.json</code> (mode 0600) or system keyring.
            </p>
          </div>
        </div>

        {/* Server & Networking */}
        <div className="bg-bg-card p-6 rounded-2xl border border-bg-border space-y-4 shadow-sm">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Server className="w-4 h-4 text-accent-cyan" /> Local Loopback Networking
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-gray-300">Host (Loopback Only)</label>
              <input
                type="text"
                disabled
                value={host}
                className="w-full bg-bg-surface border border-bg-border rounded-xl px-3.5 py-2 text-xs text-gray-400 font-mono cursor-not-allowed"
              />
              <p className="text-[11px] text-gray-500">Hard-bound to 127.0.0.1 for local isolation.</p>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-gray-300">Backend Port</label>
              <input
                type="text"
                value={port}
                onChange={(e) => setPort(e.target.value)}
                className="w-full bg-bg-surface border border-bg-border rounded-xl px-3.5 py-2 text-xs text-white font-mono outline-none focus:border-accent-primary"
              />
            </div>
          </div>
        </div>

        {/* Storage Paths */}
        <div className="bg-bg-card p-6 rounded-2xl border border-bg-border space-y-4 shadow-sm">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Folder className="w-4 h-4 text-accent-cyan" /> Storage Directories
          </h2>

          <div className="space-y-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-gray-300">Primary Models Root</label>
              <input
                type="text"
                value={modelsPath}
                onChange={(e) => setModelsPath(e.target.value)}
                className="w-full bg-bg-surface border border-bg-border rounded-xl px-3.5 py-2 text-xs text-white font-mono outline-none focus:border-accent-primary"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-gray-300">Generations Output Directory</label>
              <input
                type="text"
                value={outputPath}
                onChange={(e) => setOutputPath(e.target.value)}
                className="w-full bg-bg-surface border border-bg-border rounded-xl px-3.5 py-2 text-xs text-white font-mono outline-none focus:border-accent-primary"
              />
            </div>
          </div>
        </div>

        {/* Engine Paths */}
        <div className="bg-bg-card p-6 rounded-2xl border border-bg-border space-y-4 shadow-sm">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Server className="w-4 h-4 text-accent-cyan" /> Engine Executables & Paths
          </h2>

          <div className="space-y-3">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-gray-300">llama.cpp Executable</label>
              <input
                type="text"
                value={llamaPath}
                onChange={(e) => setLlamaPath(e.target.value)}
                className="w-full bg-bg-surface border border-bg-border rounded-xl px-3.5 py-2 text-xs text-white font-mono outline-none focus:border-accent-primary"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-gray-300">Forge Root Directory</label>
              <input
                type="text"
                value={forgePath}
                onChange={(e) => setForgePath(e.target.value)}
                className="w-full bg-bg-surface border border-bg-border rounded-xl px-3.5 py-2 text-xs text-white font-mono outline-none focus:border-accent-primary"
              />
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="submit"
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-accent-primary hover:bg-accent-primary/90 text-white font-semibold text-xs shadow-lg shadow-accent-primary/20 transition"
          >
            <Save className="w-4 h-4" />
            <span>Save Settings</span>
          </button>
        </div>
      </form>
    </div>
  );
};
