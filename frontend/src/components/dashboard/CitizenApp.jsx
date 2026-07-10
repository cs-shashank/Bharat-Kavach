import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Camera, User, Phone, MoreVertical, ShieldAlert, WifiOff, CheckCircle } from 'lucide-react';

// Feature: bharat-kavach-complete
// Requirements: 8.1–8.8
export const TRANSLATIONS = {
  en: {
    alertTitle: "Bharat Kavach Intelligence Alert",
    stagePrefix: "Scam Stage:",
    reportBtn: "REPORT",
    helplineBtn: "CALL 1930",
    safeMessage: "✓ Message appears safe. Stay cautious.",
    offlineFallback: "Could not analyze. Please call 1930 immediately.",
    unknownStage: "Scam detected",
  },
  hi: {
    alertTitle: "भारत कवच खुफिया अलर्ट",
    stagePrefix: "घोटाले का चरण:",
    reportBtn: "रिपोर्ट करें",
    helplineBtn: "1930 पर कॉल करें",
    safeMessage: "✓ संदेश सुरक्षित लगता है। सावधान रहें।",
    offlineFallback: "विश्लेषण नहीं हो सका। तुरंत 1930 पर कॉल करें।",
    unknownStage: "धोखाधड़ी पहचानी गई",
  },
  ta: {
    alertTitle: "பாரத் கவச் புலனாய்வு எச்சரிக்கை",
    stagePrefix: "மோசடி நிலை:",
    reportBtn: "புகாரளி",
    helplineBtn: "1930 அழை",
    safeMessage: "✓ செய்தி பாதுகாப்பானது. கவனமாக இருங்கள்.",
    offlineFallback: "பகுப்பாய்வு முடியவில்லை. உடனே 1930 அழையுங்கள்.",
    unknownStage: "மோசடி கண்டறியப்பட்டது",
  },
};

const LANGUAGE_OPTIONS = [
  { code: 'en', label: 'EN' },
  { code: 'hi', label: 'हिन्दी' },
  { code: 'ta', label: 'தமிழ்' },
];

// Animated typing indicator dots
const TypingDots = () => (
  <motion.div
    className="flex items-center gap-1 px-4 py-3"
    initial="hidden"
    animate="visible"
    variants={{
      visible: { transition: { staggerChildren: 0.18 } },
    }}
  >
    {[0, 1, 2].map((i) => (
      <motion.span
        key={i}
        className="w-2 h-2 rounded-full bg-slate-400 inline-block"
        variants={{
          hidden: { opacity: 0.3 },
          visible: {
            opacity: [0.3, 1, 0.3],
            transition: { duration: 1, repeat: Infinity, ease: 'easeInOut' },
          },
        }}
      />
    ))}
  </motion.div>
);

const CitizenApp = () => {
  const [messages, setMessages] = useState([
    { id: 1, text: "Hello, this is Inspector Rathore from Mumbai Cyber Cell.", sender: "stranger" },
    { id: 2, text: "Your Aadhaar is linked to an illegal Narcotic delivery.", sender: "stranger" },
  ]);
  const [input, setInput] = useState("");
  const [language, setLanguage] = useState("en");
  const [loading, setLoading] = useState(false);
  const [alertState, setAlertState] = useState(null);

  const t = TRANSLATIONS[language];

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userText = input;
    setMessages((prev) => [...prev, { id: Date.now(), text: userText, sender: "me" }]);
    setInput("");
    setLoading(true);
    setAlertState(null);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    try {
      const response = await fetch("http://localhost:8000/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript: userText }),
        signal: controller.signal,
      });

      const data = await response.json();
      const risk_score = data.risk_score ?? (data.confidence * 100);
      setAlertState({ score: risk_score, stage: data.stage });
    } catch {
      setAlertState({ offline: true });
    } finally {
      clearTimeout(timeoutId);
      setLoading(false);
    }
  };

  // Build the rendered message list — append typing indicator without mutating state
  const renderedMessages = loading
    ? [...messages, { id: "typing", sender: "typing" }]
    : messages;

  return (
    <div className="flex flex-col items-center gap-3">
      {/* Language Selector — above the phone frame */}
      <div className="flex gap-2">
        {LANGUAGE_OPTIONS.map(({ code, label }) => (
          <button
            key={code}
            onClick={() => setLanguage(code)}
            className={`px-3 py-1 rounded-full text-xs font-bold transition-colors duration-150 ${
              language === code
                ? "bg-blue-600 text-white shadow-md shadow-blue-500/30"
                : "text-slate-500 bg-slate-800 hover:text-slate-300"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Phone Frame */}
      <div className="max-w-[400px] w-full bg-[#0b141a] h-[700px] rounded-[3rem] border-[12px] border-[#222] shadow-2xl relative overflow-hidden flex flex-col font-sans">
        {/* WhatsApp Header */}
        <div className="bg-[#202c33] p-4 pt-10 flex items-center justify-between text-white">
          <div className="flex items-center gap-3">
            <div className="bg-slate-600 p-2 rounded-full"><User size={18} /></div>
            <div>
              <p className="text-sm font-bold tracking-tight">CBI / Cyber Cell (Offi...)</p>
              <p className="text-[10px] text-green-500 font-bold">Online</p>
            </div>
          </div>
          <div className="flex gap-4 opacity-70">
            <Phone size={18} />
            <MoreVertical size={18} />
          </div>
        </div>

        {/* Message Area */}
        <div
          className="flex-1 p-4 space-y-4 overflow-y-auto bg-[#0b141a] custom-scrollbar"
          style={{
            backgroundImage: 'url("https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png")',
            backgroundSize: 'contain',
            backgroundBlendMode: 'soft-light',
          }}
        >
          <AnimatePresence>
            {renderedMessages.map((msg) => {
              if (msg.sender === "typing") {
                return (
                  <motion.div
                    key="typing"
                    initial={{ opacity: 0, scale: 0.9, y: 10 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    className="max-w-[80%] bg-[#202c33] self-start rounded-xl rounded-tl-none"
                  >
                    <TypingDots />
                  </motion.div>
                );
              }
              return (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, scale: 0.9, y: 10 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  className={`max-w-[80%] p-3 rounded-xl text-sm ${
                    msg.sender === 'me'
                      ? 'bg-[#005c4b] self-end rounded-tr-none ml-auto'
                      : 'bg-[#202c33] self-start rounded-tl-none text-white'
                  }`}
                >
                  {msg.text}
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>

        {/* Alert Banner — only shown after analysis */}
        <AnimatePresence>
          {alertState && (
            <motion.div
              key="alert-banner"
              initial={{ y: 50, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 50, opacity: 0 }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="mx-4 mb-2"
            >
              {/* Offline fallback */}
              {alertState.offline && (
                <div className="p-3 bg-amber-950/60 border border-amber-500/40 rounded-xl flex items-center gap-3">
                  <WifiOff className="text-amber-400 shrink-0" size={18} />
                  <p className="text-[11px] text-amber-300 font-semibold">{t.offlineFallback}</p>
                </div>
              )}

              {/* High-risk alert (score >= 60) */}
              {!alertState.offline && alertState.score >= 60 && (
                <div className="p-3 bg-red-950/60 border border-red-500/40 rounded-xl flex items-start gap-3">
                  <ShieldAlert className="text-red-500 shrink-0 mt-0.5" size={18} />
                  <div className="flex-1 min-w-0">
                    <p className="text-[10px] font-black text-red-500 uppercase tracking-tighter">
                      {t.alertTitle}
                    </p>
                    <p className="text-[10px] text-slate-400 mt-0.5">
                      {t.stagePrefix} {alertState.stage ?? t.unknownStage}
                    </p>
                  </div>
                  <div className="flex flex-col gap-1 shrink-0">
                    <button className="bg-red-600 text-white text-[9px] font-black px-2 py-1 rounded shadow-lg shadow-red-600/20 whitespace-nowrap">
                      {t.reportBtn}
                    </button>
                    <button className="bg-slate-700 text-white text-[9px] font-black px-2 py-1 rounded whitespace-nowrap">
                      {t.helplineBtn}
                    </button>
                  </div>
                </div>
              )}

              {/* Safe message (score < 60) */}
              {!alertState.offline && alertState.score < 60 && (
                <div className="p-3 bg-green-950/60 border border-green-500/40 rounded-xl flex items-center gap-3">
                  <CheckCircle className="text-green-400 shrink-0" size={18} />
                  <p className="text-[11px] text-green-300 font-semibold">{t.safeMessage}</p>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Footer / Input */}
        <div className="bg-[#202c33] p-4 flex items-center gap-3">
          <Camera size={20} className="text-slate-400" />
          <div className="flex-1 bg-[#2a3942] rounded-lg px-4 py-2 text-white text-sm">
            <input
              type="text"
              placeholder="Type a message"
              className="w-full bg-transparent border-none focus:ring-0 outline-none"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
              disabled={loading}
            />
          </div>
          <button
            onClick={sendMessage}
            disabled={loading}
            className="bg-[#00a884] p-2 rounded-full text-white shadow-lg shadow-[#00a884]/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default CitizenApp;
