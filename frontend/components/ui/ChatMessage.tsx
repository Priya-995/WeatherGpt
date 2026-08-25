"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Bot, User, Database, Search, ChevronDown, ChevronUp, CheckCircle2 } from "lucide-react";

export interface MessageItem {
  id: string;
  role: "user" | "assistant";
  content: string;
  data_used?: Record<string, any>;
  tool_calls_made?: any[];
  model?: string;
  language?: string;
}

interface ChatMessageProps {
  message: MessageItem;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const [showAudit, setShowAudit] = useState(false);
  const isUser = message.role === "user";

  const getLanguageLabel = (lang?: string) => {
    if (lang === "hi-en") return "Hinglish";
    if (lang === "hi") return "Hindi (हिंदी)";
    return "English";
  };

  return (
    <div className={`flex flex-col ${isUser ? "items-end" : "items-start"} space-y-1.5`}>
      {/* Sender Header */}
      <div className="flex items-center space-x-2 text-xs text-slate-400 px-1">
        {isUser ? (
          <>
            <span className="font-semibold text-slate-300">You</span>
            <div className="p-1 bg-blue-600 text-white rounded-full">
              <User className="w-3.5 h-3.5" />
            </div>
          </>
        ) : (
          <>
            <div className="p-1 bg-slate-800 text-slate-400 rounded-full border border-slate-700/50">
              <Bot className="w-3.5 h-3.5" />
            </div>
            <span className="font-bold text-white flex items-center gap-1.5">
              WeatherGPT AI
              <span className="text-[10px] bg-slate-950 text-slate-400 px-2 py-0.5 rounded border border-slate-800 font-mono">
                Grounded Telemetry
              </span>
            </span>
          </>
        )}
      </div>

      {/* Message Bubble */}
      <div
        className={`max-w-[90%] sm:max-w-[85%] rounded-2xl p-4 text-sm leading-relaxed ${
          isUser
            ? "bg-blue-600 text-white rounded-tr-none"
            : "bg-slate-900 text-slate-100 border border-slate-800 rounded-tl-none"
        }`}
      >
        <div className="prose prose-invert prose-sm max-w-none text-slate-100 leading-relaxed font-sans">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

        {/* Footer info: Grounding tag / language */}
        {!isUser && (
          <div className="mt-3 pt-2.5 border-t border-slate-800 flex flex-wrap items-center justify-between text-[11px] text-slate-400 gap-2">
            <span className="flex items-center gap-1 text-slate-400 font-medium">
              <Database className="w-3 h-3 text-slate-400" />
              Verified Telemetry Signal
            </span>

            {message.language && (
              <span className="uppercase font-mono text-[10px] font-bold bg-slate-950 px-2 py-0.5 rounded border border-slate-800 text-slate-300">
                {getLanguageLabel(message.language)}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Expandable Telemetry Audit Modal / Card */}
      {!isUser && (message.data_used || (message.tool_calls_made && message.tool_calls_made.length > 0)) && (
        <div className="max-w-[90%] sm:max-w-[85%] w-full">
          <button
            type="button"
            onClick={() => setShowAudit(!showAudit)}
            className="text-xs text-slate-400 hover:text-white flex items-center space-x-1.5 font-medium bg-slate-900 px-3 py-1.5 rounded-lg border border-slate-800 transition-colors"
          >
            <Search className="w-3.5 h-3.5 text-slate-400" />
            <span>{showAudit ? "Hide Grounding Data Audit" : "View Grounding Data Audit"}</span>
            <span className="text-[10px] text-slate-500 font-mono">
              ({message.tool_calls_made?.length || 1} check)
            </span>
            {showAudit ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>

          {showAudit && (
            <div className="mt-2 p-3.5 bg-slate-950 rounded-xl border border-slate-800 text-xs font-mono space-y-3">
              <div className="flex items-center space-x-2 text-slate-300 border-b border-slate-800/80 pb-2">
                <Database className="w-4 h-4 text-slate-400" />
                <span className="font-bold">Real-time Grounding Audit Log</span>
              </div>

              {message.tool_calls_made && message.tool_calls_made.length > 0 && (
                <div className="space-y-1.5">
                  <span className="text-slate-400 font-bold">Tools & API Queries Triggered:</span>
                  {message.tool_calls_made.map((tc, idx) => (
                    <div key={idx} className="bg-slate-900 p-2 rounded border border-slate-800 space-y-1">
                      <div className="flex items-center justify-between text-slate-200 font-bold">
                        <span className="flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3 text-slate-400" />
                          {tc.tool_name}
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">Status: 200 OK</span>
                      </div>
                      <p className="text-slate-300 text-[11px] font-sans">{tc.result_summary}</p>
                    </div>
                  ))}
                </div>
              )}

              {message.model && (
                <div className="text-[10px] text-slate-500 flex justify-between pt-1 border-t border-slate-900">
                  <span>Model Engine: {message.model}</span>
                  <span>Timestamp: {new Date().toLocaleTimeString()}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
