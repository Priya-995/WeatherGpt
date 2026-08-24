"use client";

import { useState } from "react";
import { ChatResponse, sendChat } from "@/lib/api";

interface MessageItem {
  id: string;
  role: "user" | "assistant";
  content: string;
  data_used?: Record<string, any>;
  tool_calls_made?: any[];
  model?: string;
}

export default function ChatPage() {
  const [inputMessage, setInputMessage] = useState("");
  const [messages, setMessages] = useState<MessageItem[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hello! I am WeatherGPT, your grounded weather AI assistant. Ask me anything like 'Will it rain tomorrow in Noida?' or 'Is Goa safe to visit this weekend?'",
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || loading) return;

    const userText = inputMessage.trim();
    setInputMessage("");

    const userMsg: MessageItem = {
      id: Date.now().toString(),
      role: "user",
      content: userText,
    };

    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const res: ChatResponse = await sendChat(userText, sessionId);

      if (res.session_id) {
        setSessionId(res.session_id);
      }

      const assistantMsg: MessageItem = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.answer,
        data_used: res.data_used,
        tool_calls_made: res.tool_calls_made,
        model: res.model,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: MessageItem = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Sorry, I encountered an error: ${err.message || "Failed to process question."}`,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      {/* Header */}
      <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <span>🤖</span> WeatherGPT AI Assistant
          </h1>
          <p className="text-xs text-slate-400">
            Answers grounded in real Open-Meteo & IMD data. Zero hallucinated numbers.
          </p>
        </div>
        {sessionId && (
          <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-1 rounded font-mono">
            Session: {sessionId.slice(0, 8)}...
          </span>
        )}
      </div>

      {/* Chat Messages */}
      <div className="bg-slate-900/40 rounded-xl border border-slate-800 p-4 min-h-[450px] max-h-[600px] overflow-y-auto space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={msg.id}
            className={`flex flex-col ${
              msg.role === "user" ? "items-end" : "items-start"
            }`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-blue-600 text-white rounded-br-none shadow-md"
                  : "bg-slate-800 text-slate-100 border border-slate-700/80 rounded-bl-none shadow-md"
              }`}
            >
              <div className="whitespace-pre-wrap">{msg.content}</div>

              {/* Model Tag */}
              {msg.model && (
                <div className="mt-2 pt-2 border-t border-slate-700/50 text-[10px] text-slate-400 flex items-center justify-between">
                  <span>Model: {msg.model}</span>
                </div>
              )}
            </div>

            {/* Expandable Source Data Used Section */}
            {msg.role === "assistant" && (msg.data_used || msg.tool_calls_made) && (
              <div className="mt-2 max-w-[85%] w-full">
                <button
                  onClick={() => setExpandedIndex(expandedIndex === idx ? null : idx)}
                  className="text-xs text-blue-400 hover:text-blue-300 flex items-center space-x-1 font-medium bg-slate-900/80 px-3 py-1 rounded border border-slate-800 transition-colors"
                >
                  <span>🔍 {expandedIndex === idx ? "Hide Source Data Used" : "View Source Data Used"}</span>
                  <span className="text-[10px]">({msg.tool_calls_made?.length || 0} tool call(s))</span>
                </button>

                {expandedIndex === idx && (
                  <div className="mt-2 p-3 bg-slate-950 rounded-lg border border-slate-800 text-xs font-mono space-y-3">
                    {/* Tool Calls Audit Trail */}
                    {msg.tool_calls_made && msg.tool_calls_made.length > 0 && (
                      <div>
                        <div className="font-semibold text-slate-300 mb-1">Tools Executed:</div>
                        <ul className="space-y-1 text-slate-400">
                          {msg.tool_calls_made.map((tc, tIdx) => (
                            <li key={tIdx} className="bg-slate-900 p-1.5 rounded border border-slate-800">
                              <span className="text-blue-400 font-bold">{tc.tool_name}</span>
                              ({JSON.stringify(tc.arguments)}) → {tc.result_summary}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Raw Data JSON */}
                    {msg.data_used && Object.keys(msg.data_used).length > 0 && (
                      <div>
                        <div className="font-semibold text-slate-300 mb-1">Raw Weather Data JSON:</div>
                        <pre className="p-2 bg-slate-900 rounded text-[11px] text-teal-300 overflow-x-auto max-h-48 border border-slate-800">
                          {JSON.stringify(msg.data_used, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-800/80 text-slate-300 rounded-2xl rounded-bl-none px-4 py-3 text-sm flex items-center space-x-2 border border-slate-700/60">
              <div className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
              <span>Analyzing weather telemetry & reasoning...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          placeholder="Ask a question (e.g. Will it rain tomorrow evening in Noida?)"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          className="flex-1 bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
        />
        <button
          type="submit"
          disabled={loading || !inputMessage.trim()}
          className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold px-6 py-3 rounded-xl text-sm transition-colors shrink-0 shadow-lg shadow-blue-600/30"
        >
          Send
        </button>
      </form>
    </div>
  );
}
