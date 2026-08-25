"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { ChatResponse, sendChat } from "@/lib/api";

interface MessageItem {
  id: string;
  role: "user" | "assistant";
  content: string;
  data_used?: Record<string, any>;
  tool_calls_made?: any[];
  model?: string;
  language?: string;
}

const HINGLISH_KEYWORDS = [
  "kya", "kyu", "kyun", "kaise", "kaisa", "kaisi", "kab", "kahan", "kaha", "kidhar",
  "kon", "kaun", "kitna", "kitni", "kitne", "kal", "aaj", "parso", "subah", "shaam",
  "raat", "dopahar", "din", "mausam", "barish", "barsaat", "baarish", "paani", "pani",
  "hawa", "badal", "dhoop", "garmi", "thand", "sardi", "toofan", "aandhi", "tapman",
  "fasal", "khet", "kheti", "kisaan", "kisano", "spray", "pesticide", "fertilizer",
  "khad", "kar", "kare", "karein", "karna", "karega", "karegi", "karenge", "sakta",
  "sakti", "sakte", "chahiye", "hoga", "hogi", "honge", "hai", "hain", "hoon", "hu",
  "tha", "thi", "the", "rahega", "rahegi", "rahenge", "batao", "bataiye", "boliye",
  "bata", "dekh", "dekho", "mera", "meri", "mere", "mujhe", "mujhko", "hum", "hume",
  "humein", "humara", "humari", "humare", "aap", "aapka", "aapki", "aapke", "tum",
  "tumhara", "tumhari", "tumhare", "accha", "theek", "bhi", "nahi", "mat", "karo",
  "pehle", "baad", "mein", "me", "par", "se", "ko", "ka", "ki", "ke", "namaste",
  "chhatri", "gaadi", "chalo", "jaana"
];

const LANGUAGE_LABELS: Record<string, string> = {
  "en": "English",
  "hi": "हिंदी (Hindi)",
  "hi-en": "Hinglish",
  "bn": "বাংলা (Bengali)",
  "ta": "தமிழ் (Tamil)",
  "te": "తెలుగు (Telugu)",
  "mr": "मराठी (Marathi)",
  "gu": "ગુજરાતી (Gujarati)",
  "pa": "ਪੰਜਾਬੀ (Punjabi)",
  "kn": "ಕನ್ನಡ (Kannada)",
  "ml": "മലയാളം (Malayalam)",
  "ur": "اردو (Urdu)",
  "es": "Español",
  "fr": "Français",
  "de": "Deutsch",
};

export default function ChatPage() {
  const [inputMessage, setInputMessage] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState<"auto" | "en" | "hi" | "hi-en">("auto");
  const [messages, setMessages] = useState<MessageItem[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hello! I am WeatherGPT. Ask me weather & farming questions in **English**, **हिंदी (Hindi)**, **Hinglish**, or any language (e.g. *'Kal pesticide spray kar sakta hoon?'*, *'क्या कल बारिश होगी?'*). I will automatically detect your language and respond in the same language!",
      language: "en",
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  // Client-side language detection helper
  const detectLanguage = (text: string): string => {
    const trimmed = text.trim();
    if (!trimmed) return "en";

    // 1. Script-based Unicode detection
    if (/[\u0900-\u097F]/.test(trimmed)) return "hi"; // Devanagari (Hindi/Marathi)
    if (/[\u0980-\u09FF]/.test(trimmed)) return "bn"; // Bengali
    if (/[\u0B80-\u0BFF]/.test(trimmed)) return "ta"; // Tamil
    if (/[\u0C00-\u0C7F]/.test(trimmed)) return "te"; // Telugu
    if (/[\u0A80-\u0AFF]/.test(trimmed)) return "gu"; // Gujarati
    if (/[\u0A00-\u0A7F]/.test(trimmed)) return "pa"; // Punjabi
    if (/[\u0C80-\u0CFF]/.test(trimmed)) return "kn"; // Kannada
    if (/[\u0D00-\u0D7F]/.test(trimmed)) return "ml"; // Malayalam
    if (/[\u0600-\u06FF]/.test(trimmed)) return "ur"; // Urdu

    // 2. Hinglish (Romanized Hindi) keyword & phrase detection
    const lower = trimmed.toLowerCase();
    const words = lower.match(/\b[a-z]+\b/g) || [];
    const matchedHinglish = words.filter((w) => HINGLISH_KEYWORDS.includes(w));

    if (matchedHinglish.length >= 1) {
      return "hi-en";
    }

    return "en";
  };

  const getLanguageName = (code?: string) => {
    if (!code) return "English";
    return LANGUAGE_LABELS[code.toLowerCase()] || code.toUpperCase();
  };

  const sendQuery = async (queryText: string) => {
    if (!queryText.trim() || loading) return;

    const userText = queryText.trim();
    setInputMessage("");

    // Determine effective language to send
    const detected = detectLanguage(userText);
    const langToSend = selectedLanguage === "auto" ? "auto" : selectedLanguage;
    const userMsgLang = selectedLanguage === "auto" ? detected : selectedLanguage;

    const userMsg: MessageItem = {
      id: Date.now().toString(),
      role: "user",
      content: userText,
      language: userMsgLang,
    };

    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const res: ChatResponse = await sendChat(userText, sessionId, langToSend);

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
        language: res.language || (selectedLanguage === "auto" ? detected : selectedLanguage),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errorMsg: MessageItem = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: userMsgLang === "hi"
          ? "क्षमा करें, मौसम सेवा से कनेक्ट करने में असमर्थ। कृपया कुछ क्षण बाद पुनः प्रयास करें।"
          : userMsgLang === "hi-en"
          ? "Sorry, abhi weather service se connect nahi ho pa raha hai. Kripya thodi der baad dobara try karein."
          : "Sorry, I am unable to connect to the weather service right now. Please try asking your question again in a moment.",
        language: userMsgLang,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await sendQuery(inputMessage);
  };

  const samplePrompts = [
    { label: "🌦️ English", text: "Will it rain tomorrow evening in Noida?" },
    { label: "🌧️ हिंदी", text: "क्या कल दिल्ली में बारिश होगी और तापमान कितना रहेगा?" },
    { label: "🌾 Hinglish", text: "Kal Bhopal me pesticide spray kar sakta hoon kya?" },
    { label: "☀️ Mumbai", text: "Mumbai me aaj dhoop aur humidity kaisa hai?" },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      {/* Header & Language Selector */}
      <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <span>🤖</span> WeatherGPT AI Assistant
          </h1>
          <p className="text-xs text-slate-400">
            Multilingual AI grounded in real weather data with automatic language matching.
          </p>
        </div>

        {/* Language Selector Buttons */}
        <div className="flex items-center space-x-1.5 bg-slate-950 p-1.5 rounded-lg border border-slate-800">
          <span className="text-[11px] text-slate-400 font-medium px-2">Language:</span>
          <button
            type="button"
            onClick={() => setSelectedLanguage("auto")}
            className={`px-2.5 py-1 text-xs rounded-md font-semibold transition-colors flex items-center gap-1 ${
              selectedLanguage === "auto"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-slate-400 hover:text-white"
            }`}
            title="Automatically detect user's language and respond in the same language"
          >
            <span>✨</span> Auto-Detect
          </button>
          <button
            type="button"
            onClick={() => setSelectedLanguage("en")}
            className={`px-2.5 py-1 text-xs rounded-md font-semibold transition-colors ${
              selectedLanguage === "en"
                ? "bg-blue-600 text-white"
                : "text-slate-400 hover:text-white"
            }`}
          >
            English
          </button>
          <button
            type="button"
            onClick={() => setSelectedLanguage("hi-en")}
            className={`px-2.5 py-1 text-xs rounded-md font-semibold transition-colors ${
              selectedLanguage === "hi-en"
                ? "bg-emerald-600 text-white"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Hinglish
          </button>
          <button
            type="button"
            onClick={() => setSelectedLanguage("hi")}
            className={`px-2.5 py-1 text-xs rounded-md font-semibold transition-colors ${
              selectedLanguage === "hi"
                ? "bg-amber-600 text-white"
                : "text-slate-400 hover:text-white"
            }`}
          >
            हिंदी
          </button>
        </div>
      </div>

      {/* Quick Prompt Suggestions */}
      <div className="flex flex-wrap gap-2 items-center text-xs">
        <span className="text-slate-500 font-medium">Quick Try:</span>
        {samplePrompts.map((p, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => sendQuery(p.text)}
            className="bg-slate-900/80 hover:bg-slate-800 text-slate-300 hover:text-white px-2.5 py-1 rounded-lg border border-slate-800 transition-colors text-xs"
          >
            <span className="font-semibold text-blue-400 mr-1">{p.label}:</span>
            <span>&ldquo;{p.text}&rdquo;</span>
          </button>
        ))}
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
              {/* Formatted Markdown Output */}
              <div className="prose prose-invert prose-sm max-w-none text-slate-100 leading-relaxed">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>

              {/* Language Tag */}
              {msg.language && (
                <div className="mt-2 pt-2 border-t border-slate-700/50 text-[10px] text-slate-400 flex items-center justify-between gap-2">
                  <span>{msg.role === "user" ? "Input Language" : "WeatherGPT Response"}</span>
                  <span className="uppercase font-mono font-bold bg-slate-900/80 px-1.5 py-0.5 rounded text-blue-300">
                    {getLanguageName(msg.language)}
                  </span>
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
                  <span>🔍 {expandedIndex === idx ? "Hide Telemetry Audit" : "View Telemetry Audit"}</span>
                  <span className="text-[10px]">({msg.tool_calls_made?.length || 0} data source check(s))</span>
                </button>

                {expandedIndex === idx && (
                  <div className="mt-2 p-3 bg-slate-950 rounded-lg border border-slate-800 text-xs font-mono space-y-3">
                    {/* Tool Calls Audit Trail */}
                    {msg.tool_calls_made && msg.tool_calls_made.length > 0 && (
                      <div>
                        <div className="font-semibold text-slate-300 mb-1">Data Sources Queried:</div>
                        <ul className="space-y-1 text-slate-400">
                          {msg.tool_calls_made.map((tc, tIdx) => (
                            <li key={tIdx} className="bg-slate-900 p-1.5 rounded border border-slate-800">
                              <span className="text-blue-400 font-bold">{tc.tool_name}</span> → {tc.result_summary}
                            </li>
                          ))}
                        </ul>
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
              <span>Checking real-time weather telemetry & generating answer in matching language...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          placeholder={
            selectedLanguage === "auto"
              ? "Ask in any language (e.g. 'Will it rain in Noida?', 'क्या कल बारिश होगी?', 'Kal spray kar sakta hoon?')..."
              : selectedLanguage === "hi-en"
              ? "Hinglish me pucho (e.g. Kal pesticide spray kar sakta hoon?)..."
              : selectedLanguage === "hi"
              ? "हिंदी में पूछें (उदा. क्या कल बारिश होगी?)..."
              : "Ask a question in English (e.g. Will it rain tomorrow evening in Noida?)..."
          }
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
