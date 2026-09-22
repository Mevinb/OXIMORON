import React, { useState, useEffect } from 'react';
import {
  Layers,
  Search,
  RefreshCw,
  Star,
  HardDrive,
  Sparkles,
  MessageSquare,
  Copy,
  Check,
} from 'lucide-react';
import { api, ModelItem } from '../../lib/api';
import { NavDestination } from '../../components/Sidebar';

interface ModelsPageProps {
  onNavigate: (tab: NavDestination) => void;
}

export const ModelsPage: React.FC<ModelsPageProps> = ({ onNavigate }) => {
  const [models, setModels] = useState<ModelItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedRole, setSelectedRole] = useState<string>('all');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const loadModels = async () => {
    try {
      const data = await api.getModels();
      setModels(data);
    } catch (err: any) {
      console.error('Failed to load models:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadModels();
  }, []);

  const handleScan = async () => {
    setScanning(true);
    try {
      await api.scanModels();
      await loadModels();
    } catch (err: any) {
      alert(`Model scan failed: ${err.message}`);
    } finally {
      setScanning(false);
    }
  };

  const handleToggleFavorite = async (model: ModelItem) => {
    try {
      const updated = await api.toggleFavoriteModel(model.id);
      setModels((prev) => prev.map((m) => (m.id === updated.id ? updated : m)));
    } catch (err: any) {
      console.error('Failed to toggle favorite:', err);
    }
  };

  const handleCopyPath = (path: string, id: string) => {
    navigator.clipboard.writeText(path);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const roles = [
    { id: 'all', label: 'All Models' },
    { id: 'llm', label: 'LLM (Chat)' },
    { id: 'image_checkpoint', label: 'Checkpoints' },
    { id: 'clip', label: 'CLIP' },
    { id: 't5', label: 'T5 Encoder' },
    { id: 'vae', label: 'VAE' },
    { id: 'lora', label: 'LoRA' },
  ];

  const filtered = models.filter((m) => {
    const matchesRole = selectedRole === 'all' || m.role.toLowerCase() === selectedRole.toLowerCase();
    const matchesSearch =
      !search ||
      m.name.toLowerCase().includes(search.toLowerCase()) ||
      m.locations.some((l) => l.display_path.toLowerCase().includes(search.toLowerCase()));
    return matchesRole && matchesSearch;
  });

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto overflow-y-auto h-[calc(100vh-3.5rem)] pb-16">
      {/* Top Controls Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-bg-card p-5 rounded-2xl border border-bg-border shadow-sm">
        <div className="flex-1 flex flex-col sm:flex-row items-center gap-3">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name or file path..."
              className="w-full bg-bg-surface border border-bg-border rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-gray-500 outline-none focus:border-accent-primary"
            />
          </div>

          {/* Role pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto w-full py-1">
            {roles.map((r) => (
              <button
                key={r.id}
                onClick={() => setSelectedRole(r.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition ${
                  selectedRole === r.id
                    ? 'bg-accent-primary text-white shadow-sm'
                    : 'bg-bg-surface text-gray-400 hover:text-white hover:bg-bg-border'
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleScan}
          disabled={scanning}
          className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-accent-cyan hover:bg-accent-cyan/90 disabled:opacity-50 text-bg-main font-semibold text-xs shadow-lg shadow-accent-cyan/20 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${scanning ? 'animate-spin' : ''}`} />
          <span>{scanning ? 'Scanning Filesystem...' : 'Scan Storage'}</span>
        </button>
      </div>

      {/* Stats row */}
      <div className="flex items-center justify-between text-xs text-gray-400 px-1 font-mono">
        <span>Showing {filtered.length} of {models.length} registered models</span>
        <span>Safe Parsers: GGUF Magic + Safetensors JSON Header</span>
      </div>

      {/* Model Cards Grid */}
      {loading ? (
        <div className="p-16 text-center text-sm text-gray-500">Loading model library...</div>
      ) : filtered.length === 0 ? (
        <div className="p-16 text-center bg-bg-card rounded-2xl border border-bg-border space-y-3">
          <Layers className="w-10 h-10 text-gray-600 mx-auto" />
          <div className="text-sm font-medium text-gray-300">No models found</div>
          <p className="text-xs text-gray-500 max-w-sm mx-auto">
            Try adjusting your search criteria or click "Scan Storage" to index local model files.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((model) => {
            const primaryLoc = model.locations[0];
            const sizeGb = primaryLoc ? (primaryLoc.byte_size / 1e9).toFixed(2) : '0';
            const isLlm = model.role === 'llm';

            return (
              <div
                key={model.id}
                className="bg-bg-card border border-bg-border hover:border-gray-600 rounded-2xl p-5 flex flex-col justify-between gap-4 transition shadow-sm group"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded bg-bg-surface border border-bg-border text-accent-cyan">
                        {model.format}
                      </span>
                      <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-accent-primary/15 text-accent-primary border border-accent-primary/20">
                        {model.role}
                      </span>
                      {model.quantization && (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-bg-surface text-gray-400 border border-bg-border">
                          {model.quantization}
                        </span>
                      )}
                    </div>

                    <button
                      onClick={() => handleToggleFavorite(model)}
                      className={`p-1.5 rounded-lg transition ${
                        model.favorite
                          ? 'text-accent-amber hover:bg-accent-amber/10'
                          : 'text-gray-600 hover:text-gray-400 hover:bg-bg-surface'
                      }`}
                      title={model.favorite ? 'Favorited' : 'Favorite model'}
                    >
                      <Star className={`w-4 h-4 ${model.favorite ? 'fill-accent-amber' : ''}`} />
                    </button>
                  </div>

                  <div>
                    <h3 className="font-semibold text-white text-sm group-hover:text-accent-cyan transition line-clamp-1">
                      {model.name}
                    </h3>
                    <div className="flex items-center gap-1.5 text-xs text-gray-400 font-mono mt-1">
                      <HardDrive className="w-3.5 h-3.5 text-gray-500" />
                      <span>{sizeGb} GB</span>
                    </div>
                  </div>

                  {primaryLoc && (
                    <div className="bg-bg-surface/80 rounded-xl p-2.5 border border-bg-border flex items-center justify-between gap-2 text-[11px] font-mono text-gray-400">
                      <span className="truncate" title={primaryLoc.display_path}>
                        {primaryLoc.display_path}
                      </span>
                      <button
                        onClick={() => handleCopyPath(primaryLoc.display_path, model.id)}
                        className="p-1 text-gray-500 hover:text-white shrink-0"
                        title="Copy path"
                      >
                        {copiedId === model.id ? (
                          <Check className="w-3.5 h-3.5 text-accent-emerald" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  )}
                </div>

                <div className="pt-3 border-t border-bg-border/60 flex items-center justify-between">
                  <span className="text-[11px] font-mono text-gray-500">
                    ID: {model.id.slice(0, 8)}
                  </span>
                  <button
                    onClick={() => onNavigate(isLlm ? 'chat' : 'create')}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-bg-surface hover:bg-accent-primary/20 text-accent-primary hover:text-accent-cyan border border-bg-border text-xs font-medium transition"
                  >
                    {isLlm ? (
                      <>
                        <MessageSquare className="w-3.5 h-3.5" />
                        <span>Chat Studio</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>Image Studio</span>
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
