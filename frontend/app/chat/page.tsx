"use client";

import {
  useEffect,
  useRef,
  useState,
} from "react";
import type { FormEvent } from "react";
import { sendChat } from "@/lib/api";
import type { ChatResponse } from "@/lib/api";
import ChatBubble from "@/components/ui/ChatBubble";
import LiveIndicator from "@/components/ui/LiveIndicator";
import type { MessageItem } from "@/components/ui/ChatMessage";
import {
  Bot,
  Send,
  Languages,
  HelpCircle,
  Loader2,
  Sparkles,
} from "lucide-react";

type ChatLanguage =
  | "auto"
  | "en"
  | "hi"
  | "hi-en";

type DetectedLanguage =
  | "en"
  | "hi"
  | "hi-en";

const HINGLISH_KEYWORDS = new Set([
  "kya",
  "kyu",
  "kyun",
  "kaise",
  "kab",
  "kahan",
  "kaun",
  "kitna",
  "kitni",
  "kal",
  "aaj",
  "parso",
  "subah",
  "shaam",
  "raat",
  "mausam",
  "barish",
  "baarish",
  "paani",
  "pani",
  "hawa",
  "badal",
  "dhoop",
  "garmi",
  "thand",
  "sardi",
  "toofan",
  "aandhi",
  "tapman",
  "fasal",
  "khet",
  "kheti",
  "kisaan",
  "spray",
  "pesticide",
  "fertilizer",
  "khad",
  "kar",
  "kare",
  "karein",
  "karna",
  "sakta",
  "sakti",
  "sakte",
  "chahiye",
  "hoga",
  "hogi",
  "hai",
  "hain",
  "hoon",
  "batao",
  "bataiye",
  "mera",
  "meri",
  "mujhe",
  "hum",
  "aap",
  "tum",
  "nahi",
  "karo",
  "pehle",
  "baad",
  "mein",
  "chhatri",
  "gaadi",
  "jaana",
]);

export default function ChatPage() {
  const [inputMessage, setInputMessage] =
    useState("");

  const [
    selectedLanguage,
    setSelectedLanguage,
  ] = useState<ChatLanguage>("auto");

  const [messages, setMessages] =
    useState<MessageItem[]>([
      {
        id: "welcome",
        role: "assistant",
        content:
          '**Welcome to WeatherGPT AI Decision Support.**\n\nI am your grounded meteorological assistant with **automatic language detection**. Ask me weather and agricultural timing questions in English, Hindi, or Hinglish — for example:\n- *"Will it rain in Noida this evening?"*\n- *"Kal pesticide spray kar sakta hoon?"*\n- *"क्या बाड़मेर में लू की चेतावनी है?"*',
        model:
          "WeatherGPT Groq Intelligence Engine",
        language: "en",
      },
    ]);

  const [loading, setLoading] =
    useState(false);

  const [sessionId, setSessionId] =
    useState<string | undefined>();

  const chatBottomRef =
    useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "end",
    });
  }, [messages, loading]);

  const detectLanguage = (
    text: string
  ): DetectedLanguage => {
    // Hindi/Devanagari characters
    if (/[\u0900-\u097F]/.test(text)) {
      return "hi";
    }

    const words =
      text.toLowerCase().match(/[a-z]+/g) ??
      [];

    const numberOfHinglishWords =
      words.reduce(
        (count, word) =>
          HINGLISH_KEYWORDS.has(word)
            ? count + 1
            : count,
        0
      );

    /*
     * At least two matched words are required
     * to reduce incorrect Hinglish detection.
     */
    if (numberOfHinglishWords >= 2) {
      return "hi-en";
    }

    return "en";
  };

  const handleSend = async (
    textToSend: string
  ) => {
    const userText = textToSend.trim();

    if (!userText || loading) {
      return;
    }

    setInputMessage("");

    const detectedLanguage =
      detectLanguage(userText);

    const effectiveLanguage:
      DetectedLanguage =
      selectedLanguage === "auto"
        ? detectedLanguage
        : selectedLanguage;

    const userMessage: MessageItem = {
      id: `user-${Date.now()}`,
      role: "user",
      content: userText,
      language: effectiveLanguage,
    };

    setMessages((previousMessages) => [
      ...previousMessages,
      userMessage,
    ]);

    setLoading(true);

    try {
      /*
       * This sends the question to the backend.
       * "auto" is sent when Auto is selected.
       */
      const response: ChatResponse =
        await sendChat(
          userText,
          sessionId,
          selectedLanguage
        );

      if (response.session_id) {
        setSessionId(response.session_id);
      }

      const responseLanguage = (
        response.language ||
        effectiveLanguage
      ) as MessageItem["language"];

      const assistantMessage: MessageItem = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: response.answer,
        data_used: response.data_used,
        tool_calls_made:
          response.tool_calls_made,
        model: response.model,
        language: responseLanguage,
      };

      setMessages((previousMessages) => [
        ...previousMessages,
        assistantMessage,
      ]);
    } catch (error) {
      console.error(
        "WeatherGPT chat request failed:",
        error
      );

      let errorContent =
        "Unable to connect to the weather decision support engine right now. Please try again shortly.";

      if (effectiveLanguage === "hi") {
        errorContent =
          "क्षमा करें, मौसम निर्णय सहायता इंजन से कनेक्ट करने में असमर्थ। कृपया कुछ क्षण बाद पुनः प्रयास करें।";
      }

      if (effectiveLanguage === "hi-en") {
        errorContent =
          "Sorry, abhi weather decision support engine se connect nahi ho pa raha hai. Kripya thodi der baad dobara try karein.";
      }

      const errorMessage: MessageItem = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: errorContent,
        language: effectiveLanguage,
      };

      setMessages((previousMessages) => [
        ...previousMessages,
        errorMessage,
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();
    void handleSend(inputMessage);
  };

  const promptShortcuts = [
    {
      label: "🌦️ Rain Forecast",
      text: "Will it rain in Noida today?",
    },
    {
      label: "🌾 Pesticide Spray",
      text: "Kal pesticide spray kar sakta hoon?",
    },
    {
      label: "🌡️ हिंदी में पूछें",
      text: "क्या कल दिल्ली में बारिश होगी?",
    },
    {
      label: "☀️ Heat Wave Check",
      text: "Is there a heatwave warning in Rajasthan?",
    },
  ];

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      {/* Chat header */}
      <div className="flex flex-col items-start justify-between gap-4 rounded-xl border border-surface-container-high bg-surface-container-lowest p-5 shadow-sm sm:flex-row sm:items-center">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <div className="rounded-lg bg-primary p-1.5 text-on-primary">
              <Bot className="h-5 w-5" />
            </div>

            <h1 className="text-headline-sm font-bold tracking-tight text-on-surface">
              WeatherGPT AI Decision Support
            </h1>
          </div>

          <p className="text-body-sm text-on-surface-variant">
            Natural-language assistant grounded
            in real-time NWP telemetry and IMD
            bulletins with automatic language
            matching.
          </p>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-3">
          <LiveIndicator status="connected" />

          {/* Language selector */}
          <div className="flex items-center space-x-1 rounded-lg border border-outline-variant/40 bg-surface-container p-1">
            <Languages className="ml-1 h-3.5 w-3.5 text-on-surface-variant" />

            <button
              type="button"
              onClick={() =>
                setSelectedLanguage("auto")
              }
              className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-bold transition-all ${
                selectedLanguage === "auto"
                  ? "bg-primary text-on-primary shadow-sm"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              <Sparkles className="h-3 w-3" />
              Auto
            </button>

            <button
              type="button"
              onClick={() =>
                setSelectedLanguage("en")
              }
              className={`rounded-md px-2.5 py-1 text-xs font-bold transition-all ${
                selectedLanguage === "en"
                  ? "bg-primary text-on-primary shadow-sm"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              EN
            </button>

            <button
              type="button"
              onClick={() =>
                setSelectedLanguage("hi-en")
              }
              className={`rounded-md px-2.5 py-1 text-xs font-bold transition-all ${
                selectedLanguage === "hi-en"
                  ? "bg-primary text-on-primary shadow-sm"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              Hinglish
            </button>

            <button
              type="button"
              onClick={() =>
                setSelectedLanguage("hi")
              }
              className={`rounded-md px-2.5 py-1 text-xs font-bold transition-all ${
                selectedLanguage === "hi"
                  ? "bg-primary text-on-primary shadow-sm"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              हिंदी
            </button>
          </div>
        </div>
      </div>

      {/* Suggested questions */}
      <div className="scrollbar-none flex items-center space-x-2 overflow-x-auto pb-1">
        <span className="flex shrink-0 items-center gap-1 text-label-caps text-on-surface-variant">
          <HelpCircle className="h-3.5 w-3.5 text-outline" />
          Suggested:
        </span>

        {promptShortcuts.map((prompt) => (
          <button
            key={prompt.label}
            type="button"
            disabled={loading}
            onClick={() =>
              void handleSend(prompt.text)
            }
            className="shrink-0 rounded-lg border border-outline-variant/40 bg-surface-container-lowest px-3 py-1.5 text-body-sm font-medium text-on-surface-variant transition-all hover:bg-surface-container hover:text-on-surface disabled:cursor-not-allowed disabled:opacity-50"
          >
            {prompt.label}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div className="min-h-[460px] max-h-[600px] space-y-4 overflow-y-auto rounded-xl border border-surface-container-high bg-surface-container-low p-4 sm:p-6">
        {messages.map((message) => (
          <ChatBubble
            key={message.id}
            message={message}
          />
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="flex items-center space-x-3 rounded-2xl rounded-tl-none border border-surface-container-high bg-surface-container-lowest p-4 text-body-sm text-on-surface-variant shadow-sm">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />

              <span>
                Querying telemetry data sources
                and compiling a grounded
                response...
              </span>
            </div>
          </div>
        )}

        <div ref={chatBottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="flex gap-2"
      >
        <input
          type="text"
          value={inputMessage}
          onChange={(event) =>
            setInputMessage(event.target.value)
          }
          placeholder={
            selectedLanguage === "auto"
              ? "Ask in English, Hindi, or Hinglish..."
              : selectedLanguage === "hi-en"
                ? "Hinglish me apna sawal puchho..."
                : selectedLanguage === "hi"
                  ? "हिंदी में अपना प्रश्न पूछें..."
                  : "Ask a weather question..."
          }
          aria-label="Weather question"
          className="min-w-0 flex-1 rounded-xl border border-outline-variant/40 bg-surface-container-lowest px-4 py-3 text-body-sm text-on-surface shadow-sm transition-all placeholder:text-on-surface-variant/60 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
        />

        <button
          type="submit"
          disabled={
            loading || !inputMessage.trim()
          }
          className="flex shrink-0 items-center space-x-2 rounded-xl bg-primary px-6 py-3 text-body-sm font-bold text-on-primary shadow-sm transition-all hover:bg-primary-container disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="hidden sm:inline">
                Sending
              </span>
            </>
          ) : (
            <>
              <span className="hidden sm:inline">
                Send
              </span>
              <Send className="h-4 w-4" />
            </>
          )}
        </button>
      </form>
    </div>
  );
}