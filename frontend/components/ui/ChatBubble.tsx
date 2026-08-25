"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import { Bot, User, Database, CheckCircle2 } from "lucide-react";
import { MessageItem } from "./ChatMessage";

interface ChatBubbleProps {
  message: MessageItem;
}

export default function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex flex-col ${isUser ? "items-end" : "items-start"} space-y-1.5`}>
      {/* Header Label */}
      <div className="flex items-center space-x-2 text-xs text-on-surface-variant px-1">
        {isUser ? (
          <>
            <span className="font-medium text-on-surface">You</span>
            <div className="p-1 bg-secondary text-on-secondary rounded-full">
              <User className="w-3.5 h-3.5" />
            </div>
          </>
        ) : (
          <>
            <div className="p-1 bg-primary text-on-primary rounded-full">
              <Bot className="w-3.5 h-3.5" />
            </div>
            <span className="font-semibold text-primary flex items-center gap-1.5">
              WeatherGPT AI
              <span className="text-[10px] bg-surface-container text-on-surface-variant px-2 py-0.5 rounded border border-outline-variant/40 font-mono">
                Grounded LLM
              </span>
            </span>
          </>
        )}
      </div>

      {/* Message Bubble */}
      <div
        className={`max-w-[90%] sm:max-w-[85%] rounded-2xl p-4 text-body-sm leading-relaxed shadow-sm ${
          isUser
            ? "bg-secondary text-on-secondary rounded-tr-none"
            : "bg-primary-container/20 text-on-surface border border-primary-container/30 rounded-tl-none"
        }`}
      >
        <div className="prose prose-sm max-w-none text-current leading-relaxed font-sans">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

        {/* Small "Source:" / "Based on:" Grounding Line */}
        {!isUser && (
          <div className="mt-3 pt-2.5 border-t border-outline-variant/30 flex flex-wrap items-center justify-between text-[11px] text-on-surface-variant gap-2">
            <span className="flex items-center gap-1 font-mono text-outline">
              <Database className="w-3 h-3 text-primary" />
              Source: Open-Meteo telemetry & IMD alerts (Updated {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})
            </span>

            {message.language && (
              <span className="uppercase font-mono text-[10px] font-bold bg-surface-container px-2 py-0.5 rounded text-primary">
                {message.language === "hi-en" ? "Hinglish" : message.language === "hi" ? "Hindi" : "English"}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
