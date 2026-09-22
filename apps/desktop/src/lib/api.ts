export interface StatusSummary {
  status: string;
  supervisor_id: string;
  active_engines: number;
  active_jobs: number;
  cpu_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  gpu_available: boolean;
}

export interface GpuInfo {
  index: number;
  name: string;
  total_memory_bytes: number;
  used_memory_bytes: number;
  free_memory_bytes: number;
  utilization_pct: number | null;
  temperature_c: number | null;
  power_draw_w: number | null;
  power_limit_w: number | null;
}

export interface SystemSnapshot {
  timestamp: string;
  cpu_utilization_pct: number;
  ram_total_bytes: number;
  ram_used_bytes: number;
  ram_free_bytes: number;
  disks: Record<string, { total_bytes: number; used_bytes: number; free_bytes: number }>;
  gpus: GpuInfo[];
  gpu_status: { available: boolean; reason: string | null };
}

export interface EngineItem {
  id: string;
  adapter_key: string;
  display_name: string;
  config_key: string;
  version: string | null;
  observed_state: string;
  endpoint: string | null;
  capabilities: {
    tasks: string[];
    supported_formats: string[];
    streaming: boolean;
  };
}

export interface ModelItem {
  id: string;
  name: string;
  role: string;
  format: string;
  quantization?: string;
  favorite: boolean;
  locations: Array<{
    display_path: string;
    byte_size: number;
  }>;
}

export interface MessageItem {
  id: string;
  role: 'system' | 'user' | 'assistant';
  content: string;
  status: string;
  created_at: string;
}

export interface ConversationItem {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages?: MessageItem[];
}

export interface GenerationItem {
  id: string;
  prompt: string;
  negative_prompt: string;
  seed: number;
  duration_ms: number;
  status: string;
  created_at: string;
  artifacts: Array<{
    id: string;
    relative_path: string;
    media_type: string;
    byte_size: number;
  }>;
}

export interface LogItem {
  id: string;
  timestamp: string;
  level: string;
  component: string;
  message: string;
}

class ApiService {
  private token: string = '';

  setToken(token: string) {
    this.token = token;
  }

  getToken(): string {
    return this.token;
  }

  getArtifactUrl(artifactId: string): string {
    return `/api/v1/artifacts/${artifactId}/content${this.token ? `?token=${encodeURIComponent(this.token)}` : ''}`;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`/api/v1${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ error: { message: response.statusText } }));
      throw new Error(err.error?.message || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async getSession(): Promise<{ token: string; supervisor_id: string }> {
    const res = await fetch('/api/v1/session');
    if (!res.ok) throw new Error('Failed to fetch session');
    return res.json();
  }

  async getStatus(): Promise<StatusSummary> {
    return this.request<StatusSummary>('/status');
  }

  async getSystem(): Promise<SystemSnapshot> {
    return this.request<SystemSnapshot>('/system');
  }

  async getEngines(): Promise<EngineItem[]> {
    return this.request<EngineItem[]>('/engines');
  }

  async discoverEngines(): Promise<EngineItem[]> {
    return this.request<EngineItem[]>('/engines/discover', { method: 'POST' });
  }

  async startEngine(id: string): Promise<any> {
    return this.request(`/engines/${id}/start`, { method: 'POST' });
  }

  async stopEngine(id: string): Promise<any> {
    return this.request(`/engines/${id}/stop`, { method: 'POST' });
  }

  async getModels(role?: string, search?: string): Promise<ModelItem[]> {
    const params = new URLSearchParams();
    if (role) params.set('role', role);
    if (search) params.set('search', search);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return this.request<ModelItem[]>(`/models${qs}`);
  }

  async scanModels(): Promise<{ status: string; discovered_count: number }> {
    return this.request('/models/scan', { method: 'POST' });
  }

  async toggleFavoriteModel(id: string): Promise<ModelItem> {
    return this.request<ModelItem>(`/models/${id}`, { method: 'PATCH' });
  }

  async getConversations(): Promise<ConversationItem[]> {
    return this.request<ConversationItem[]>('/conversations');
  }

  async getConversation(id: string): Promise<ConversationItem> {
    return this.request<ConversationItem>(`/conversations/${id}`);
  }

  async streamChat(
    message: string,
    conversationId?: string,
    onDelta?: (token: string) => void,
    onDone?: () => void,
    onError?: (err: any) => void
  ) {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    try {
      const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
          stream: true,
        }),
      });

      if (!response.ok) {
        throw new Error(`Chat error: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) return;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const raw = line.slice(6).trim();
            if (raw === '[DONE]') {
              onDone?.();
              return;
            }
            try {
              const data = JSON.parse(raw);
              if (data.delta) {
                onDelta?.(data.delta);
              }
            } catch {
              // ignore partial lines
            }
          }
        }
      }
      onDone?.();
    } catch (err) {
      onError?.(err);
    }
  }

  async generateImage(payload: {
    prompt: string;
    negative_prompt?: string;
    width?: number;
    height?: number;
    steps?: number;
    seed?: number;
  }): Promise<GenerationItem> {
    return this.request<GenerationItem>('/generate/image', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getGenerations(): Promise<GenerationItem[]> {
    return this.request<GenerationItem[]>('/generations');
  }

  async getLogs(level?: string, limit: number = 100): Promise<{ entries: LogItem[] }> {
    const params = new URLSearchParams();
    if (level && level !== 'ALL') params.set('level', level);
    params.set('limit', String(limit));
    return this.request(`/logs?${params.toString()}`);
  }

  async getSettings(): Promise<any> {
    return this.request('/settings');
  }

  async saveSettings(settings: any): Promise<any> {
    return this.request('/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    });
  }
}

export const api = new ApiService();
