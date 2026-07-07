import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Camera, User, Phone, MoreVertical, ShieldAlert } from 'lucide-react';

const CitizenApp = () => {
  const [messages, setMessages] = useState([
    { id: 1, text: "Hello, this is Inspector Rathore from Mumbai Cyber Cell.", sender: "stranger" },
    { id: 2, text: "Your Aadhaar is linked to an illegal Narcotic delivery.", sender: "stranger" },
  ]);
  const [input, setInput] = useState("");

  const sendMessage = () => {
    if (!input.trim()) return;
    setMessages([...messages, { id: Date.now(), text: input, sender: "me" }]);
    setInput("");
  };

  return (
    <div className="max-w-[400px] mx-auto bg-[#0b141a] h-[700px] rounded-[3rem] border-[12px] border-[#222] shadow-2xl relative overflow-hidden flex flex-col font-sans">
      {/* WhatsApp Header Simulation */}
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
      <div className="flex-1 p-4 space-y-4 overflow-y-auto bg-[#0b141a] custom-scrollbar" style={{ backgroundImage: 'url("https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png")', backgroundSize: 'contain', backgroundBlendMode: 'soft-light' }}>
        <AnimatePresence>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, scale: 0.9, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              className={`max-w-[80%] p-3 rounded-xl text-sm ${msg.sender === 'me' ? 'bg-[#005c4b] self-end rounded-tr-none' : 'bg-[#202c33] self-start rounded-tl-none text-white'}`}
            >
              {msg.text}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Security Banner Hook */}
      <motion.div 
        initial={{ y: 50 }}
        animate={{ y: 0 }}
        className="m-4 p-3 bg-red-950/50 border border-red-500/30 rounded-xl flex items-center gap-3"
      >
        <ShieldAlert className="text-red-500 shrink-0" size={20} />
        <div className="flex-1">
          <p className="text-[10px] font-black text-red-500 uppercase tracking-tighter">Bharat Kavach Intelligence Alert</p>
          <p className="text-[10px] text-slate-400">Scam pattern detected: "Digital Arrest" logic identified.</p>
        </div>
        <button className="bg-red-600 text-white text-[10px] font-black px-2 py-1 rounded shadow-lg shadow-red-600/20">
          REPORT
        </button>
      </motion.div>

      {/* Footer / Input */}
      <div className="bg-[#202c33] p-4 flex items-center gap-3">
        <Camera size={20} className="text-slate-400" />
        <div className="flex-1 bg-[#2a3942] rounded-lg px-4 py-2 text-white text-sm">
          <input 
            type="text" 
            placeholder="Type a message" 
            className="w-full bg-transparent border-none focus:ring-0" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          />
        </div>
        <button 
          onClick={sendMessage}
          className="bg-[#00a884] p-2 rounded-full text-white shadow-lg shadow-[#00a884]/20"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
};

export default CitizenApp;
