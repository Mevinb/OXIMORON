import React, { useState, useEffect, useRef } from 'react';
import {
  MessageSquare,
  Plus,
  Send,
  Square,
  Sparkles,
  Bot,
  User,
  Cpu,
  AlertCircle,
  Clock,
} from 'lucide-react';
import { api, ConversationItem, EngineItem, MessageItem, isEngineRunning } from '../../lib/api';

export const ChatPage: React.FC = () => {
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [streamDelta, setStreamDelta] = useState('');
  const [engines, setEngines] = useState<EngineItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadConversations = async () => {
    try {
      const convs = await api.getConversations();
      setConversations(convs);
      if (convs.length > 0 && !activeConversationId) {
        setActiveConversationId(convs[0].id);
      }
    } catch (err: any) {
      console.error('Failed to load conversations:', err);
    }
  };

  const loadEngines = async () => {
    try {
      const engs = await api.getEngines();
      setEngines(engs);
    } catch (err: any) {
      console.error('Failed to load engines:', err);
    }
  };

  const loadActiveConversation = async (id: string) => {
    try {
      const conv = await api.getConversation(id);
      if (conv.messages) {
        setMessages(conv.messages);
      }
    } catch (err: any) {
      console.error('Failed to load conversation messages:', err);
    }
  };

  useEffect(() => {
    loadConversations();
    loadEngines();
  }, []);

  useEffect(() => {
    if (activeConversationId) {
      loadActiveConversation(activeConversationId);
    } else {
      setMessages([]);
    }
  }, [activeConversationId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamDelta]);

  const handleStartNewChat = () => {
    setActiveConversationId(null);
    setMessages([]);
    setStreamDelta('');
    setError(null);
  };

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputMessage.trim() || streaming) return;

    const userText = inputMessage.trim();
    setInputMessage('');
    setError(null);

    // Optimistically add user message
    const tempUserMsg: MessageItem = {
      id: `tmp-${Date.now()}`,
      role: 'user',
      content: userText,
      status: 'completed',
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setStreaming(true);
    setStreamDelta('');

    let accumulatedDelta = '';

    await api.streamChat(
      userText,
      activeConversationId || undefined,
      (delta) => {
        accumulatedDelta += delta;
        setStreamDelta(accumulatedDelta);
      },
      async () => {
        // Stream completed
        setStreaming(false);
        setStreamDelta('');
        await loadConversations();
        if (activeConversationId) {
          await loadActiveConversation(activeConversationId);
        }
      },
      (err) => {
        setStreaming(false);
        setError(err?.message || 'Chat generation failed. Ensure llama.cpp engine is running.');
      }
    );
  };

  const llamaEngine = engines.find((e) => e.adapter_key === 'llamacpp');
  const isLlamaRunning = isEngineRunning(llamaEngine?.observed_state);

  return (
    <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden">
      {/* Left Conversations Sidebar */}
      <div className="w-72 bg-bg-surface border-r border-bg-border flex flex-col justify-between">
        <div className="p-3 border-b border-bg-border/60">
          <button
            onClick={handleStartNewChat}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-accent-primary hover:bg-accent-primary/90 text-white font-medium text-xs shadow-lg shadow-accent-primary/20 transition"
          >
            <Plus className="w-4 h-4" />
            <span>New Chat</span>
          </button>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {conversations.length === 0 ? (
            <div className="text-center py-10 text-xs text-gray-500 font-sans">
              No conversations yet. Start a new chat!
            </div>
          ) : (
            conversations.map((conv) => {
              const isActive = conv.id === activeConversationId;
              return (
                <button
                  key={conv.id}
                  onClick={() => setActiveConversationId(conv.id)}
                  className={`w-full text-left p-3 rounded-xl transition flex flex-col gap-1 border ${
                    isActive
                      ? 'bg-accent-primary/15 border-accent-primary/30 text-white shadow-sm'
                      : 'border-transparent text-gray-400 hover:text-gray-200 hover:bg-bg-card'
                  }`}
                >
                  <div className="flex items-center gap-2 font-medium text-xs truncate">
                    <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-accent-cyan' : 'text-gray-500'}`} />
                    <span className="truncate">{conv.title || 'Untitled Chat'}</span>
                  </div>
                  <div className="flex items-center gap-1 text-[10px] text-gray-500 font-mono">
                    <Clock className="w-2.5 h-2.5" />
                    <span>{new Date(conv.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                </button>
              );
            })
          )}
        </div>

        {/* Engine status indicator */}
        <div className="p-3 border-t border-bg-border/60 bg-bg-card/40 m-2 rounded-xl border border-bg-border text-xs">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-gray-400 font-mono text-[11px]">
              <Cpu className="w-3.5 h-3.5 text-accent-cyan" /> llama.cpp
            </span>
            <span
              className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-medium ${
                isLlamaRunning
                  ? 'bg-accent-emerald/20 text-accent-emerald'
                  : 'bg-gray-800 text-gray-400'
              }`}
            >
              {isLlamaRunning ? 'RUNNING' : 'STOPPED'}
            </span>
          </div>
          {!isLlamaRunning && (
            <button
              onClick={async () => {
                if (llamaEngine) {
                  await api.startEngine(llamaEngine.id);
                  await loadEngines();
                }
              }}
              className="mt-2 w-full py-1 rounded bg-bg-surface hover:bg-bg-border text-accent-primary hover:text-accent-cyan text-[11px] font-medium transition"
            >
              Start llama-server
            </button>
          )}
        </div>
      </div>

      {/* Main Chat Panel */}
      <div className="flex-1 flex flex-col justify-between bg-bg-main">
        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {messages.length === 0 && !streaming ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-accent-primary to-accent-cyan p-[2px] shadow-xl shadow-accent-primary/20">
                <div className="w-full h-full bg-bg-card rounded-2xl flex items-center justify-center text-accent-cyan">
                  <Sparkles className="w-7 h-7" />
                </div>
              </div>
              <div className="max-w-md">
                <h3 className="text-lg font-bold text-white">Local Chat Studio</h3>
                <p className="text-xs text-gray-400 mt-1.5">
                  Send a prompt to begin conversation with your local GGUF model via llama.cpp. All inputs and outputs remain completely on your local machine.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3 max-w-lg w-full pt-4">
                {[
                  'Explain quantum computing in simple terms',
                  'Write a Python function to parse JSON safely',
                  'Summarize the key benefits of local-first AI',
                  'Create an SQL schema for model registry',
                ].map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setInputMessage(prompt);
                    }}
                    className="p-3 text-left rounded-xl bg-bg-card border border-bg-border hover:border-accent-primary/50 text-xs text-gray-300 hover:text-white transition shadow-sm"
                  >
                    "{prompt}"
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-4 w-full">
              {messages.map((msg) => {
                const isUser = msg.role === 'user';
                return (
                  <div
                    key={msg.id}
                    className={`flex items-start gap-3.5 ${isUser ? 'flex-row-reverse' : ''}`}
                  >
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 text-white shadow-sm ${
                        isUser
                          ? 'bg-accent-primary'
                          : 'bg-bg-card border border-bg-border text-accent-cyan'
                      }`}
                    >
                      {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                    </div>

                    <div
                      className={`p-4 rounded-2xl max-w-[82%] text-sm leading-relaxed ${
                        isUser
                          ? 'bg-accent-primary text-white shadow-md shadow-accent-primary/10 rounded-tr-none'
                          : 'bg-bg-card border border-bg-border text-gray-200 rounded-tl-none font-sans whitespace-pre-wrap'
                      }`}
                    >
                      {msg.content}
                    </div>
                  </div>
                );
              })}

              {/* In-flight streaming message */}
              {streaming && streamDelta && (
                <div className="flex items-start gap-3.5">
                  <div className="w-8 h-8 rounded-lg bg-bg-card border border-bg-border flex items-center justify-center shrink-0 text-accent-cyan">
                    <Bot className="w-4 h-4 animate-pulse" />
                  </div>
                  <div className="p-4 rounded-2xl max-w-[82%] text-sm leading-relaxed bg-bg-card border border-bg-border text-gray-200 rounded-tl-none font-sans whitespace-pre-wrap">
                    {streamDelta}
                    <span className="inline-block w-2 h-4 ml-1 bg-accent-cyan animate-pulse align-middle" />
                  </div>
                </div>
              )}

              {/* Streaming placeholder before first token */}
              {streaming && !streamDelta && (
                <div className="flex items-start gap-3.5">
                  <div className="w-8 h-8 rounded-lg bg-bg-card border border-bg-border flex items-center justify-center shrink-0 text-accent-cyan">
                    <Bot className="w-4 h-4 animate-spin" />
                  </div>
                  <div className="p-4 rounded-2xl bg-bg-card border border-bg-border text-xs text-gray-400 rounded-tl-none font-mono">
                    Generating response...
                  </div>
                </div>
              )}

              {error && (
                <div className="p-4 rounded-xl bg-accent-rose/10 border border-accent-rose/30 text-accent-rose text-xs flex items-center gap-2.5">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-bg-border bg-bg-surface/80 backdrop-blur-md">
          <form
            onSubmit={handleSendMessage}
            className="max-w-3xl mx-auto flex items-center gap-2 bg-bg-card rounded-2xl border border-bg-border p-2 focus-within:border-accent-primary/60 shadow-lg transition"
          >
            <textarea
              rows={1}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder="Ask anything (Enter to send, Shift+Enter for new line)..."
              className="flex-1 bg-transparent border-0 outline-none text-sm text-white placeholder-gray-500 resize-none px-3 py-2 max-h-32"
            />
            {streaming ? (
              <button
                type="button"
                onClick={() => setStreaming(false)}
                className="p-2.5 rounded-xl bg-accent-rose text-white hover:bg-accent-rose/90 transition shadow-md"
                title="Stop generation"
              >
                <Square className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!inputMessage.trim()}
                className="p-2.5 rounded-xl bg-accent-primary disabled:opacity-40 hover:bg-accent-primary/90 text-white transition shadow-md shadow-accent-primary/20"
                title="Send message"
              >
                <Send className="w-4 h-4" />
              </button>
            )}
          </form>
        </div>
      </div>
    </div>
  );
};
