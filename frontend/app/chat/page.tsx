"use client";

import { useState, useRef, useEffect } from "react";
import { ChatResponse, sendChat } from "@/lib/api";
import ChatBubble from "@/components/ui/ChatBubble";
import LiveIndicator from "@/components/ui/LiveIndicator";
import { MessageItem } from "@/components/ui/ChatMessage";
import { Bot, Send, Languages, HelpCircle, Loader2 } from "lucide-react";

export default function ChatPage() {
  const [inputMessage, setInputMessage] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState<"en" | "hi" | "hi-en">("en");
  const [messages, setMessages] = useState<MessageItem[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "**Welcome to WeatherGPT AI Decision Support.**\n\nI am your grounded meteorological assistant. Ask me weather and agricultural timing questions in English, Hindi, or Hinglish — for example:\n- *\"Will it rain in Noida this evening?\"*\n- *\"Kal pesticide spray kar sakta hoon?\"*\n- *\"क्या बाड़मेर में लू की चेतावनी है?\"*",
      model: "WeatherGPT Groq Intelligence Engine",
      language: "en",
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const detectLanguage = (text: string): "en" | "hi" | "hi-en" => {
    const hinglishKeywords = ["kal", "kya", "kar", "hoon", "hai", "kaise", "sakta", "spray", "barish", "mausam", "kahan", "paani", "karo"];
    const lower = text.toLowerCase();

    if (/[\u0900-\u097F]/.test(text)) return "hi";
    if (hinglishKeywords.some((kw) => lower.includes(kw))) return "hi-en";
    return selectedLanguage;
  };

  const handleSend = async (textToSend: string) => {
    const userText = textToSend.trim();
    if (!userText || loading) return;

    setInputMessage("");
    const effectiveLang = detectLanguage(userText);

    const userMsg: MessageItem = {
      id: Date.now().toString(),
      role: "user",
      content: userText,
      language: effectiveLang,
    };

    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const res: ChatResponse = await sendChat(userText, sessionId, effectiveLang);

      if (res.session_id) setSessionId(res.session_id);

      const assistantMsg: MessageItem = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.answer,
        data_used: res.data_used,
        tool_calls_made: res.tool_calls_made,
        model: res.model,
        language: res.language || effectiveLang,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errorMsg: MessageItem = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Unable to connect to weather decision support engine right now.",
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSend(inputMessage);
  };

  const promptShortcuts = [
    { label: "Rain Forecast Noida", text: "Will it rain in Noida today?" },
    { label: "Pesticide Spray Timing", text: "Kal pesticide spray kar sakta hoon?" },
    { label: "Heat Wave Alert Check", text: "Is there a heatwave warning in Rajasthan?" },
    { label: "Travel Safety Guide", text: "Are there thunderstorm alerts for Delhi road travel tonight?" },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      {/* Header with Agent Name + LiveIndicator + Language Toggle */}
      <div className="bg-surface-container-lowest p-5 rounded-xl border border-surface-container-high shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 bg-primary text-on-primary rounded-lg">
              <Bot className="w-5 h-5" />
            </div>
            <h1 className="text-headline-sm font-bold text-on-surface tracking-tight">
              WeatherGPT AI Decision Support
            </h1>
          </div>
          <p className="text-body-sm text-on-surface-variant">
            Natural-language assistant grounded in real-time NWP telemetry & IMD bulletins.
          </p>
        </div>

        <div className="flex items-center space-x-3 shrink-0">
          <LiveIndicator status="connected" />

          {/* Language Selector (EN / HI / Hinglish) */}
          <div className="flex items-center space-x-1 bg-surface-container p-1 rounded-lg border border-outline-variant/40">
            <Languages className="w-3.5 h-3.5 text-on-surface-variant ml-1" />
            <button
              type="button"
              onClick={() => setSelectedLanguage("en")}
              className={`px-2.5 py-1 text-xs rounded-md font-bold transition-all ${
                selectedLanguage === "en"
                  ? "bg-primary text-on-primary"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              EN
            </button>
            <button
              type="button"
              onClick={() => setSelectedLanguage("hi-en")}
              className={`px-2.5 py-1 text-xs rounded-md font-bold transition-all ${
                selectedLanguage === "hi-en"
                  ? "bg-primary text-on-primary"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              Hinglish
            </button>
            <button
              type="button"
              onClick={() => setSelectedLanguage("hi")}
              className={`px-2.5 py-1 text-xs rounded-md font-bold transition-all ${
                selectedLanguage === "hi"
                  ? "bg-primary text-on-primary"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              HI
            </button>
          </div>
        </div>
      </div>

      {/* Suggested Question Chips Row */}
      <div className="flex items-center space-x-2 overflow-x-auto pb-1 scrollbar-none">
        <span className="text-label-caps text-on-surface-variant shrink-0 flex items-center gap-1">
          <HelpCircle className="w-3.5 h-3.5 text-outline" /> Suggested:
        </span>
        {promptShortcuts.map((ps, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => handleSend(ps.text)}
            className="text-body-sm bg-surface-container-lowest hover:bg-surface-container text-on-surface-variant hover:text-on-surface px-3 py-1.5 rounded-lg border border-outline-variant/40 transition-all shrink-0 font-medium"
          >
            {ps.label}
          </button>
        ))}
      </div>

      {/* Scrollable Message List */}
      <div className="bg-surface-container-low rounded-xl border border-surface-container-high p-4 sm:p-6 min-h-[460px] max-h-[600px] overflow-y-auto space-y-4">
        {messages.map((msg) => (
          <ChatBubble key={msg.id} message={msg} />
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-surface-container-lowest text-on-surface-variant rounded-2xl rounded-tl-none p-4 text-body-sm flex items-center space-x-3 border border-surface-container-high shadow-sm">
              <Loader2 className="w-4 h-4 text-primary animate-spin" />
              <span>Querying telemetry data sources & compiling grounded response...</span>
            </div>
          </div>
        )}
        <div ref={chatBottomRef} />
      </div>

      {/* Input Form with Primary Color Button */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          placeholder={
            selectedLanguage === "hi-en"
              ? "Hinglish me pucho (e.g. Kal pesticide spray kar sakta hoon?)"
              : selectedLanguage === "hi"
              ? "हिंदी में पूछें (उदा. क्या कल बारिश होगी?)"
              : "Ask a natural-language weather question (e.g. Will it rain in Noida today?)"
          }
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          className="flex-1 bg-surface-container-lowest border border-outline-variant/40 rounded-xl px-4 py-3 text-body-sm text-on-surface placeholder-on-surface-variant/60 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all shadow-sm"
        />
        <button
          type="submit"
          disabled={loading || !inputMessage.trim()}
          className="bg-primary hover:bg-primary-container disabled:opacity-50 text-on-primary font-bold px-6 py-3 rounded-xl text-body-sm transition-all shrink-0 shadow-sm flex items-center space-x-2"
        >
          <span>Send</span>
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
