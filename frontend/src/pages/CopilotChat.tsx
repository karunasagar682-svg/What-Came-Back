import React, { useState, useRef, useEffect } from 'react';
import {
  Sparkles,
  Send,
  Cpu,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Clock,
  ArrowRight,
  Terminal,
  ShieldCheck
} from 'lucide-react';
import { api } from '../services/api';
import { CopilotChatResponse } from '../types';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  provider?: string;
  tools?: Array<{ tool: string; args?: any; result?: any }>;
}

export const CopilotChat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: `### Welcome to Chat with AI\n\nI am your intelligent returns architect. I calculate deterministic recovery values across **Restock**, **Refurbish**, **Vendor Return**, **Liquidation**, and **Scrap** without financial hallucinations.\n\nAsk me anything about today's returns, aging inventory, or supplier quality risks!`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      provider: 'Deterministic Core Engine / OpenAI SDK',
    },
  ]);
  const [inputText, setInputText] = useState<string>('');
  const [isTyping, setIsTyping] = useState<boolean>(false);
  const [suggestedActions, setSuggestedActions] = useState<string[]>([
    'What needs my attention today?',
    'Why is batch HB-09 flagged?',
    'Prepare a proposed action for these 40 headphones',
    'Which vendor-return windows are closing soon?',
    'Show me the financial difference between the best route and liquidation',
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSendMessage = async (textToSend?: string) => {
    const text = textToSend || inputText;
    if (!text.trim() || isTyping) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setIsTyping(true);

    try {
      const history = messages
        .filter((m) => m.id !== 'welcome')
        .map((m) => ({ role: m.sender, content: m.text }));

      const res: CopilotChatResponse = await api.chatWithCopilot(text, history);

      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: res.response,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        provider: res.provider_used,
        tools: res.tools_called,
      };

      setMessages((prev) => [...prev, botMsg]);
      if (res.suggested_actions && res.suggested_actions.length > 0) {
        setSuggestedActions(res.suggested_actions);
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: 'assistant',
          text: `Error connecting to Copilot reasoning service: ${err.message}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          provider: 'Error Handler',
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="h-[calc(100vh-7rem)] flex flex-col max-w-5xl mx-auto bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      {/* Top Header */}
      <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-teal-500/20 border border-teal-500/40 flex items-center justify-center text-teal-300">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-sm font-extrabold text-white flex items-center space-x-2">
              <span>Chat with AI</span>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-teal-500/20 text-teal-300 border border-teal-500/30">
                Agentic Assistant
              </span>
            </h1>
            <p className="text-[11px] text-slate-400">
              Deterministic calculations + Structured explanations with tool citations
            </p>
          </div>
        </div>

        <div className="hidden sm:flex items-center space-x-2 text-[11px] text-slate-300 bg-slate-800/80 px-3 py-1 rounded-lg border border-slate-700">
          <ShieldCheck className="w-3.5 h-3.5 text-teal-400" />
          <span>Factual Grounding Active</span>
        </div>
      </div>

      {/* Chat Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-5 bg-slate-50/50">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex flex-col ${m.sender === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div
              className={`max-w-2xl rounded-2xl p-4.5 space-y-2 shadow-sm text-xs leading-relaxed ${
                m.sender === 'user'
                  ? 'bg-slate-900 text-white rounded-tr-none'
                  : 'bg-white text-slate-800 border border-slate-200 rounded-tl-none'
              }`}
            >
              {/* Message Header / Provider */}
              {m.sender === 'assistant' && (
                <div className="flex items-center justify-between text-[10px] text-slate-400 pb-2 border-b border-slate-100">
                  <span className="font-semibold text-teal-700 flex items-center space-x-1">
                    <Sparkles className="w-3 h-3 text-teal-500" />
                    <span>Gadgetbay Copilot</span>
                  </span>
                  {m.provider && (
                    <span className="px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 font-mono">
                      {m.provider}
                    </span>
                  )}
                </div>
              )}

              {/* Message Text (Markdown formatting) */}
              <div className="whitespace-pre-line prose-xs">
                {m.text}
              </div>

              {/* Tools Called Log */}
              {m.tools && m.tools.length > 0 && (
                <div className="mt-3 pt-2 border-t border-slate-100 text-[10px] space-y-1">
                  <div className="font-bold text-slate-500 flex items-center space-x-1">
                    <Terminal className="w-3 h-3 text-slate-400" />
                    <span>Backend Tools Executed:</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {m.tools.map((t, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-mono border border-slate-200"
                      >
                        {t.tool}()
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <span className="text-[10px] text-slate-400 px-2 mt-1">
              {m.timestamp}
            </span>
          </div>
        ))}

        {isTyping && (
          <div className="flex items-center space-x-2 text-xs text-slate-500 bg-white p-3 rounded-xl border border-slate-200 max-w-xs shadow-sm">
            <div className="w-2 h-2 rounded-full bg-teal-500 animate-bounce" />
            <div className="w-2 h-2 rounded-full bg-teal-500 animate-bounce delay-150" />
            <div className="w-2 h-2 rounded-full bg-teal-500 animate-bounce delay-300" />
            <span className="text-[11px] font-medium text-slate-600 ml-1">
              Evaluating routes and backend data...
            </span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Quick Prompt Buttons */}
      <div className="px-6 py-2.5 bg-white border-t border-slate-100 shrink-0">
        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5 flex items-center space-x-1">
          <HelpCircle className="w-3 h-3" />
          <span>Suggested Questions for Demo:</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {suggestedActions.map((prompt, i) => (
            <button
              key={i}
              onClick={() => handleSendMessage(prompt)}
              className="text-[11px] font-semibold text-slate-700 bg-slate-100 hover:bg-teal-50 hover:text-teal-700 hover:border-teal-300 border border-slate-200 px-2.5 py-1 rounded-lg transition"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      {/* Input Bar */}
      <div className="p-4 bg-white border-t border-slate-200 shrink-0">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="flex items-center space-x-2"
        >
          <input
            type="text"
            placeholder="Ask about today's returns, Batch HB-09, or financial recovery..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={isTyping}
            className="flex-1 px-4 py-2.5 border border-slate-300 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!inputText.trim() || isTyping}
            className="px-4 py-2.5 bg-teal-600 hover:bg-teal-500 text-white rounded-xl text-xs font-bold transition flex items-center space-x-1.5 disabled:opacity-40 shadow-sm"
          >
            <span>Send</span>
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
    </div>
  );
};
