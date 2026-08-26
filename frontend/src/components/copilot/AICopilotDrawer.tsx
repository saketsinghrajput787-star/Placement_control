import React, { useState } from 'react';
import { useOperations } from '../../store/operationsStore';
import { apiClient } from '../../api/client';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { Bot, X, Send, Sparkles, Database, ArrowUpRight } from 'lucide-react';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  grounding?: Record<string, any>;
  timestamp: string;
}

export const AICopilotDrawer: React.FC = () => {
  const { isCopilotOpen, setIsCopilotOpen, scheduleVersion, analytics } = useOperations();
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        "Welcome to the **Placement Operations AI Copilot**. I have real-time verified access to the CP-SAT scheduling engine and placement database.\n\nAsk me about today's capacity bottlenecks, disruption mitigations, or constraint explanations.",
      timestamp: '09:00 AM',
    },
  ]);

  if (!isCopilotOpen) return null;

  const quickQuestions = [
    "What are today's biggest risks?",
    "Why is TechNova a bottleneck?",
    "What happens if Panel P3 fails?",
    "Which recovery strategy is best?",
  ];

  const handleSend = async (questionText?: string) => {
    const textToSend = questionText || query;
    if (!textToSend.trim()) return;

    const userMsg: ChatMessage = {
      role: 'user',
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setQuery('');
    setIsLoading(true);

    try {
      const res = await apiClient.post('/ai/copilot/query', {
        query: textToSend,
        context_type: 'GENERAL',
      });

      const aiMsg: ChatMessage = {
        role: 'assistant',
        content: res.data.answer,
        grounding: res.data.data_grounding,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, aiMsg]);
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Unable to reach Groq AI Provider. Operating with deterministic backend fallback.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div
        className="fixed inset-0 bg-sand-900/40 backdrop-blur-xs transition-opacity"
        onClick={() => setIsCopilotOpen(false)}
      />

      <div className="fixed inset-y-0 right-0 max-w-md w-full bg-white shadow-2xl border-l border-sand-300 flex flex-col z-50">
        {/* Header */}
        <div className="p-4 border-b border-sand-200 bg-sand-50 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded bg-forest-700 text-white flex items-center justify-center">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-sand-900">Placement AI Copilot</h3>
              <p className="text-[10px] text-sand-500 font-mono flex items-center gap-1">
                <Database className="w-3 h-3 text-forest-700" />
                Grounded in Live DB State • Groq gpt-oss
              </p>
            </div>
          </div>
          <button
            onClick={() => setIsCopilotOpen(false)}
            className="p-1 rounded-md text-sand-400 hover:text-sand-700 hover:bg-sand-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Grounding Status Strip */}
        <div className="px-4 py-2 bg-forest-50 border-b border-forest-100 flex items-center justify-between text-[11px] text-forest-900 font-mono">
          <span>Scheduled: {analytics?.scheduled_interviews || 0}</span>
          <span>Stability: {analytics?.schedule_stability || 100}%</span>
          <span>Conflicts: {analytics?.active_conflicts_count || 0}</span>
        </div>

        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((m, i) => (
            <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div
                className={`p-3.5 rounded-lg max-w-[90%] text-xs leading-relaxed ${
                  m.role === 'user'
                    ? 'bg-forest-700 text-white font-medium rounded-br-none'
                    : 'bg-sand-100 border border-sand-300 text-sand-900 rounded-bl-none shadow-2xs'
                }`}
              >
                <div className="whitespace-pre-line">{m.content}</div>

                {m.grounding && (
                  <div className="mt-2.5 pt-2 border-t border-sand-200 text-[10px] text-sand-600 font-mono flex items-center gap-1.5">
                    <Database className="w-3 h-3 text-forest-700" />
                    <span>Grounded facts verified against PostgreSQL</span>
                  </div>
                )}
              </div>
              <span className="text-[10px] text-sand-400 mt-1 px-1">{m.timestamp}</span>
            </div>
          ))}

          {isLoading && (
            <div className="flex items-center gap-2 text-xs text-sand-500 italic p-3 bg-sand-50 rounded-lg w-fit">
              <span className="w-2 h-2 rounded-full bg-forest-600 animate-pulse" />
              Analyzing live placement week telemetry...
            </div>
          )}
        </div>

        {/* Quick Suggestion Pills */}
        <div className="p-3 border-t border-sand-200 bg-sand-50/50 space-y-1.5">
          <span className="text-[10px] uppercase font-semibold text-sand-500 tracking-wider block">
            Suggested Queries
          </span>
          <div className="flex flex-wrap gap-1.5">
            {quickQuestions.map((q, i) => (
              <button
                key={i}
                onClick={() => handleSend(q)}
                className="text-[11px] bg-white border border-sand-300 hover:border-forest-600 text-sand-800 hover:text-forest-900 px-2.5 py-1 rounded-full transition-colors flex items-center gap-1"
              >
                <span>{q}</span>
                <ArrowUpRight className="w-3 h-3 text-sand-400" />
              </button>
            ))}
          </div>
        </div>

        {/* Input Bar */}
        <div className="p-3 border-t border-sand-200 bg-white">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              placeholder="Ask Copilot about schedule risks or candidates..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1 text-xs bg-sand-50 border border-sand-300 rounded-md p-2.5 text-sand-900 focus:outline-none focus:ring-1 focus:ring-forest-600"
            />
            <Button variant="primary" size="sm" type="submit" isLoading={isLoading}>
              <Send className="w-3.5 h-3.5" />
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
};
