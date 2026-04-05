"use client";

import { useState, useRef, useEffect } from "react";
import {
  Send,
  Bot,
  User,
  Loader2,
  ChevronDown,
  ChevronRight,
  Wrench,
  Settings2,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface ToolCall {
  tool: string;
  input: unknown;
  output: unknown;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCall[];
  timestamp: Date;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "I'm the Widby Research Agent. I analyze scoring outputs, generate hypotheses about parameter improvements, and run controlled experiments. Share an observation or ask me to investigate a specific proxy dimension.",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [configOpen, setConfigOpen] = useState(false);
  const [config, setConfig] = useState({
    maxIterations: 10,
    budget: 50,
  });
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    if (!input.trim() || loading) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/agent/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input }),
      });
      const data = await res.json();
      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.response || "No response received.",
        toolCalls: data.tool_calls,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content:
            "Connection error. Make sure the research agent API is running on port 8000.",
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full">
      <div className="flex flex-1 flex-col">
        {/* Header */}
        <header className="flex items-center justify-between border-b border-[var(--color-dark-border)] px-6 py-4">
          <div>
            <h1 className="text-lg font-semibold">Research Agent Chat</h1>
            <p className="text-xs text-[var(--color-text-muted)]">
              Deep Agent conversation interface
            </p>
          </div>
          <button
            onClick={() => setConfigOpen(!configOpen)}
            className="flex items-center gap-2 rounded-md border border-[var(--color-dark-border)] px-3 py-1.5 text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-dark-hover)]"
          >
            <Settings2 size={14} />
            Session Config
          </button>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {messages.map((msg) => (
            <ChatBubble key={msg.id} message={msg} />
          ))}
          {loading && (
            <div className="flex items-center gap-2 text-[var(--color-text-muted)] text-sm">
              <Loader2 size={16} className="animate-spin" />
              Thinking...
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t border-[var(--color-dark-border)] px-6 py-4">
          <div className="flex items-center gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Describe an observation or ask about a proxy dimension..."
              className="flex-1 rounded-lg border border-[var(--color-dark-border)] bg-[var(--color-dark-alt)] px-4 py-2.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-accent)] focus:outline-none"
            />
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className="rounded-lg bg-[var(--color-accent)] p-2.5 text-white transition-colors hover:bg-[var(--color-accent-dark)] disabled:opacity-40"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Config drawer */}
      {configOpen && (
        <div className="w-72 border-l border-[var(--color-dark-border)] bg-[var(--color-dark-alt)] p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium">Session Config</h3>
            <button onClick={() => setConfigOpen(false)} className="text-[var(--color-text-muted)]">
              <X size={16} />
            </button>
          </div>
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-[var(--color-text-muted)] mb-1">
                Max Iterations
              </label>
              <input
                type="number"
                value={config.maxIterations}
                onChange={(e) =>
                  setConfig((c) => ({ ...c, maxIterations: +e.target.value }))
                }
                className="w-full rounded border border-[var(--color-dark-border)] bg-[var(--color-dark)] px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-[var(--color-text-muted)] mb-1">
                Budget (USD)
              </label>
              <input
                type="number"
                value={config.budget}
                onChange={(e) =>
                  setConfig((c) => ({ ...c, budget: +e.target.value }))
                }
                className="w-full rounded border border-[var(--color-dark-border)] bg-[var(--color-dark)] px-3 py-1.5 text-sm"
              />
            </div>
            <button
              onClick={async () => {
                setLoading(true);
                try {
                  const res = await fetch("/api/agent/sessions", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      max_iterations: config.maxIterations,
                      budget_limit_usd: config.budget,
                    }),
                  });
                  const data = await res.json();
                  setMessages((prev) => [
                    ...prev,
                    {
                      id: crypto.randomUUID(),
                      role: "assistant",
                      content: `Research session **${data.run_id}** completed.\n\n${data.report || "See dashboard for details."}`,
                      timestamp: new Date(),
                    },
                  ]);
                } catch {
                  setMessages((prev) => [
                    ...prev,
                    {
                      id: crypto.randomUUID(),
                      role: "assistant",
                      content: "Failed to start session. Check API connection.",
                      timestamp: new Date(),
                    },
                  ]);
                } finally {
                  setLoading(false);
                  setConfigOpen(false);
                }
              }}
              className="w-full rounded-md bg-[var(--color-accent)] py-2 text-sm font-medium text-white hover:bg-[var(--color-accent-dark)]"
            >
              Start Research Session
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ChatBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-[var(--color-accent-bg)]" : "bg-[var(--color-dark-card)]"
        )}
      >
        {isUser ? (
          <User size={14} className="text-[var(--color-accent)]" />
        ) : (
          <Bot size={14} className="text-[var(--color-accent)]" />
        )}
      </div>
      <div className={cn("max-w-[75%] space-y-2", isUser && "text-right")}>
        <div
          className={cn(
            "rounded-lg px-4 py-2.5 text-sm leading-relaxed",
            isUser
              ? "bg-[var(--color-accent)] text-white"
              : "bg-[var(--color-dark-card)] text-[var(--color-text-primary)] border border-[var(--color-dark-border)]"
          )}
        >
          <div className="whitespace-pre-wrap">{message.content}</div>
        </div>
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="space-y-1">
            {message.toolCalls.map((tc, i) => (
              <ToolCallCard key={i} toolCall={tc} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ToolCallCard({ toolCall }: { toolCall: ToolCall }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-md border border-[var(--color-dark-border)] bg-[var(--color-dark)] text-left">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-2 px-3 py-2 text-xs text-[var(--color-text-muted)]"
      >
        <Wrench size={12} className="text-[var(--color-accent)]" />
        <span className="font-mono">{toolCall.tool}</span>
        <span className="ml-auto">
          {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>
      </button>
      {expanded && (
        <div className="border-t border-[var(--color-dark-border)] px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-[var(--color-text-muted)] mb-1">
            Output
          </p>
          <pre className="overflow-x-auto text-xs text-[var(--color-text-secondary)] font-mono leading-relaxed">
            {JSON.stringify(toolCall.output, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
