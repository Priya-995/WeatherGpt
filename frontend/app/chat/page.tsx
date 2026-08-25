"use client";

import { useState, useRef, useEffect } from "react";
import { ChatResponse, sendChat } from "@/lib/api";
import ChatBubble from "@/components/ui/ChatBubble";
import LiveIndicator from "@/components/ui/LiveIndicator";
import { MessageItem } from "@/components/ui/ChatMessage";
import { Bot, Send, Languages, HelpCircle, Loader2, Sparkles } from "lucide-react";

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

export default function ChatPage() {
  const [inputMessage, setInputMessage] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState<"auto" | "en" | "hi" | "hi-en">("auto");
  const [messages, setMessages] = useState<MessageItem[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "**Welcome to WeatherGPT AI Decision Support.**\n\nI am your grounded meteorological assistant with **automatic language detection**. Ask me weather and agricultural timing questions in English, Hindi, or Hinglish — for example:\n- *\"Will it rain in Noida this evening?\"*\n- *\"Kal pesticide spray kar sakta hoon?\"*\n- *\"क्या बाड़मेर में लू की चेतावनी है?\"*",
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

  const handleSend = async (textToSend: string) => {
    const userText = textToSend.trim();
    if (!userText || loading) return;

    setInputMessage("");

    // Determine effective language
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

      if (res.session_id) setSessionId(res.session_id);

      const assistantMsg: MessageItem = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.answer,
        data_used: res.data_used,
        tool_calls_made: res.tool_calls_made,
        model: res.model,
        language: res.language || userMsgLang,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errorMsg: MessageItem = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: userMsgLang === "hi"
          ? "क्षमा करें, मौसम निर्णय सहायता इंजन से कनेक्ट करने में असमर्थ। कृपया कुछ क्षण बाद पुनः प्रयास करें।"
          : userMsgLang === "hi-en"
          ? "Sorry, abhi weather decision support engine se connect nahi ho pa raha hai. Kripya thodi der baad dobara try karein."
          : "Unable to connect to weather decision support engine right now.",
        language: userMsgLang,
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
    { label: "🌦️ Rain Forecast", text: "Will it rain in Noida today?" },
    { label: "🌾 Pesticide Spray", text: "Kal pesticide spray kar sakta hoon?" },
    { label: "🌡️ हिंदी में पूछें", text: "क्या कल दिल्ली में बारिश होगी?" },
    { label: "☀️ Heat Wave Check", text: "Is there a heatwave warning in Rajasthan?" },
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
            Natural-language assistant grounded in real-time NWP telemetry & IMD bulletins with automatic language matching.
          </p>
        </div>

        <div className="flex items-center space-x-3 shrink-0">
          <LiveIndicator status="connected" />

          {/* Language Selector (Auto / EN / Hinglish / HI) */}
          <div className="flex items-center space-x-1 bg-surface-container p-1 rounded-lg border border-outline-variant/40">
            <Languages className="w-3.5 h-3.5 text-on-surface-variant ml-1" />
            <button
              type="button"
              onClick={() => setSelectedLanguage("auto")}
              className={`px-2.5 py-1 text-xs rounded-md font-bold transition-all flex items-center gap-1 ${
                selectedLanguage === "auto"
                  ? "bg-primary text-on-primary shadow-sm"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
              title="Automatically detect user's language and respond in the same language"
            >
              <Sparkles className="w-3 h-3" />
              Auto
            </button>
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
              हिंदी
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
              <span>Querying telemetry data sources & compiling grounded response in matching language...</span>
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
            selectedLanguage === "auto"
              ? "Ask in any language (e.g. 'Will it rain in Noida?', 'क्या कल बारिश होगी?', 'Kal spray kar sakta hoon?')..."
              : selectedLanguage === "hi-en"
              ? "Hinglish me pucho (e.g. Kal pesticide spray kar sakta hoon?)..."
              : selectedLanguage === "hi"
              ? "हिंदी में पूछें (उदा. क्या कल बारिश होगी?)..."
              : "Ask a natural-language weather question (e.g. Will it rain in Noida today?)..."
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
