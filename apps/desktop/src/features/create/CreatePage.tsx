import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Sliders,
  Image as ImageIcon,
  RotateCcw,
  Download,
  Clock,
  Cpu,
  AlertCircle,
  Copy,
  Check,
} from 'lucide-react';
import { api, EngineItem, GenerationItem, isEngineRunning } from '../../lib/api';

export const CreatePage: React.FC = () => {
  const [prompt, setPrompt] = useState('hyperrealistic cinematic portrait of a neon cybernetic owl in a cyberpunk city, 8k, highly detailed, dramatic lighting');
  const [negativePrompt, setNegativePrompt] = useState('blurry, low quality, artifacts, distorted, extra limbs, ugly');
  const [width, setWidth] = useState(768);
  const [height, setHeight] = useState(768);
  const [steps, setSteps] = useState(20);
  const [seed, setSeed] = useState(-1);

  const [engines, setEngines] = useState<EngineItem[]>([]);
  const [generations, setGenerations] = useState<GenerationItem[]>([]);
  const [selectedGen, setSelectedGen] = useState<GenerationItem | null>(null);
  const [generating, setGenerating] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const loadData = async () => {
    try {
      const [engs, gens] = await Promise.all([
        api.getEngines().catch(() => []),
        api.getGenerations().catch(() => []),
      ]);
      setEngines(engs);
      setGenerations(gens);
      if (gens.length > 0 && !selectedGen) {
        setSelectedGen(gens[0]);
      }
    } catch (err: any) {
      console.error('Failed to load create page data:', err);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    let timer: any;
    if (generating) {
      setElapsedSec(0);
      timer = setInterval(() => setElapsedSec((s) => s + 1), 1000);
    } else {
      clearInterval(timer);
    }
    return () => clearInterval(timer);
  }, [generating]);

  const forgeEngine = engines.find((e) => e.adapter_key === 'forge');
  const isForgeRunning = isEngineRunning(forgeEngine?.observed_state);

  const handleGenerate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!prompt.trim() || generating) return;

    setGenerating(true);
    setError(null);

    try {
      const result = await api.generateImage({
        prompt: prompt.trim(),
        negative_prompt: negativePrompt.trim(),
        width,
        height,
        steps,
        seed: seed === -1 ? Math.floor(Math.random() * 100000000) : seed,
      });
      setSelectedGen(result);
      await loadData();
    } catch (err: any) {
      setError(
        err?.message ||
          'Image generation failed. Please verify that Forge is running with --api on loopback.'
      );
    } finally {
      setGenerating(false);
    }
  };

  const handleCopyPrompt = () => {
    if (selectedGen) {
      navigator.clipboard.writeText(selectedGen.prompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const resolutions = [
    { label: 'Square (512x512)', w: 512, h: 512 },
    { label: 'Square HD (768x768)', w: 768, h: 768 },
    { label: 'Portrait (512x768)', w: 512, h: 768 },
    { label: 'Landscape (768x512)', w: 768, h: 512 },
    { label: 'SDXL 1K (1024x1024)', w: 1024, h: 1024 },
  ];

  return (
    <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden">
      {/* Left Control Panel */}
      <div className="w-96 bg-bg-surface border-r border-bg-border flex flex-col justify-between overflow-y-auto p-5 space-y-5">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Sliders className="w-4 h-4 text-accent-cyan" /> Generation Parameters
            </h2>
            <div className="flex items-center gap-1.5 text-xs font-mono">
              <Cpu className="w-3.5 h-3.5 text-gray-400" />
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                  isForgeRunning
                    ? 'bg-accent-emerald/20 text-accent-emerald'
                    : 'bg-gray-800 text-gray-400'
                }`}
              >
                {isForgeRunning ? 'Forge Ready' : 'Forge Offline'}
              </span>
            </div>
          </div>

          {!isForgeRunning && (
            <div className="p-3 rounded-xl bg-accent-amber/10 border border-accent-amber/30 text-accent-amber text-xs space-y-2">
              <div className="flex items-center gap-2 font-medium">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>Forge engine is currently stopped</span>
              </div>
              <button
                onClick={async () => {
                  if (forgeEngine) {
                    await api.startEngine(forgeEngine.id);
                    await loadData();
                  }
                }}
                className="w-full py-1.5 rounded bg-accent-amber/20 hover:bg-accent-amber/30 text-white font-medium transition text-xs"
              >
                Start Forge Engine
              </button>
            </div>
          )}

          {/* Prompt */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-gray-300">Prompt</label>
            <textarea
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Describe the image you wish to synthesize..."
              className="w-full bg-bg-card border border-bg-border rounded-xl p-3 text-xs text-white placeholder-gray-500 outline-none focus:border-accent-cyan transition resize-none"
            />
          </div>

          {/* Negative Prompt */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-gray-300">Negative Prompt</label>
            <textarea
              rows={2}
              value={negativePrompt}
              onChange={(e) => setNegativePrompt(e.target.value)}
              placeholder="Features to avoid..."
              className="w-full bg-bg-card border border-bg-border rounded-xl p-3 text-xs text-white placeholder-gray-500 outline-none focus:border-accent-cyan transition resize-none"
            />
          </div>

          {/* Resolution Selector */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-gray-300">Resolution</label>
            <div className="grid grid-cols-1 gap-1.5">
              {resolutions.map((res) => {
                const isSelected = width === res.w && height === res.h;
                return (
                  <button
                    key={res.label}
                    type="button"
                    onClick={() => {
                      setWidth(res.w);
                      setHeight(res.h);
                    }}
                    className={`py-1.5 px-3 rounded-lg text-xs font-medium text-left transition border ${
                      isSelected
                        ? 'bg-accent-cyan/15 border-accent-cyan text-white shadow-sm'
                        : 'bg-bg-card border-bg-border text-gray-400 hover:text-white hover:bg-bg-cardHover'
                    }`}
                  >
                    {res.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Steps & Seed */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-gray-300">Steps</span>
                <span className="font-mono text-accent-cyan">{steps}</span>
              </div>
              <input
                type="range"
                min={10}
                max={50}
                value={steps}
                onChange={(e) => setSteps(Number(e.target.value))}
                className="w-full accent-accent-cyan"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-gray-300">Seed</span>
                <span className="font-mono text-gray-400">{seed === -1 ? 'Random' : seed}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <input
                  type="number"
                  value={seed}
                  onChange={(e) => setSeed(Number(e.target.value))}
                  className="w-full bg-bg-card border border-bg-border rounded-lg px-2.5 py-1 text-xs text-white font-mono outline-none focus:border-accent-cyan"
                />
                <button
                  type="button"
                  onClick={() => setSeed(-1)}
                  title="Randomize seed"
                  className="p-1.5 rounded-lg bg-bg-card border border-bg-border text-gray-400 hover:text-white"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Generate Button */}
        <div className="pt-4 border-t border-bg-border space-y-2">
          {error && (
            <div className="p-3 rounded-xl bg-accent-rose/10 border border-accent-rose/30 text-accent-rose text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span className="truncate">{error}</span>
            </div>
          )}

          <button
            onClick={handleGenerate}
            disabled={generating || !prompt.trim()}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-accent-primary to-accent-cyan hover:opacity-90 disabled:opacity-40 text-white font-semibold text-xs shadow-lg shadow-accent-cyan/20 flex items-center justify-center gap-2 transition"
          >
            {generating ? (
              <>
                <Sparkles className="w-4 h-4 animate-spin" />
                <span>Synthesizing ({elapsedSec}s)...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Generate Image</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Right Canvas / Gallery Panel */}
      <div className="flex-1 flex flex-col justify-between bg-bg-main overflow-hidden">
        {/* Main Preview */}
        <div className="flex-1 flex items-center justify-center p-6 overflow-hidden relative">
          {selectedGen && selectedGen.artifacts.length > 0 ? (
            <div className="max-w-2xl max-h-full flex flex-col items-center justify-center relative group">
              <img
                src={api.getArtifactUrl(selectedGen.artifacts[0].id)}
                alt={selectedGen.prompt}
                className="max-h-[calc(100vh-16rem)] w-auto rounded-2xl shadow-2xl border border-bg-border object-contain"
              />

              {/* Action overlay bar */}
              <div className="mt-4 flex items-center gap-3 bg-bg-surface/90 backdrop-blur-md px-4 py-2 rounded-xl border border-bg-border shadow-lg">
                <button
                  onClick={handleCopyPrompt}
                  className="flex items-center gap-1.5 text-xs text-gray-300 hover:text-white transition"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-accent-emerald" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied' : 'Copy Prompt'}</span>
                </button>

                <div className="w-[1px] h-3 bg-bg-border" />

                <a
                  href={api.getArtifactUrl(selectedGen.artifacts[0].id)}
                  download={`generation-${selectedGen.id}.png`}
                  className="flex items-center gap-1.5 text-xs text-accent-cyan hover:underline"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download</span>
                </a>

                <div className="w-[1px] h-3 bg-bg-border" />

                <span className="text-[11px] font-mono text-gray-400 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  <span>{(selectedGen.duration_ms / 1000).toFixed(1)}s</span>
                </span>
              </div>
            </div>
          ) : (
            <div className="text-center p-8 space-y-3">
              <div className="w-16 h-16 rounded-2xl bg-bg-card border border-bg-border flex items-center justify-center text-gray-500 mx-auto">
                <ImageIcon className="w-8 h-8" />
              </div>
              <div className="text-sm font-medium text-gray-400">No Image Selected</div>
              <p className="text-xs text-gray-500 max-w-sm">
                Enter a prompt and hit Generate, or select a previous creation from the reel below.
              </p>
            </div>
          )}
        </div>

        {/* Bottom Generation Filmstrip / Reel */}
        <div className="h-32 bg-bg-surface border-t border-bg-border p-3 overflow-x-auto flex items-center gap-3">
          {generations.length === 0 ? (
            <div className="text-xs text-gray-500 font-sans px-4">
              Your recent synthesized image gallery will appear here.
            </div>
          ) : (
            generations.map((gen) => {
              if (!gen.artifacts || gen.artifacts.length === 0) return null;
              const isSelected = selectedGen?.id === gen.id;
              const art = gen.artifacts[0];
              return (
                <button
                  key={gen.id}
                  onClick={() => setSelectedGen(gen)}
                  className={`h-24 w-24 shrink-0 rounded-xl overflow-hidden border-2 transition relative group ${
                    isSelected
                      ? 'border-accent-cyan shadow-lg shadow-accent-cyan/20 scale-105'
                      : 'border-bg-border hover:border-gray-500 opacity-80 hover:opacity-100'
                  }`}
                >
                  <img
                    src={api.getArtifactUrl(art.id)}
                    alt={gen.prompt}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition flex items-end p-1">
                    <span className="text-[9px] text-white font-mono truncate">
                      {gen.prompt}
                    </span>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
