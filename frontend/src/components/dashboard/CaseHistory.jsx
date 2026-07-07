import React from 'react';
import { motion } from 'framer-motion';
import { Clock, ChevronRight, Scale } from 'lucide-react';

const CaseHistory = ({ cases, onSelect }) => {
  return (
    <div className="glass-card p-4 h-full flex flex-col">
      <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2">
        <Clock size={12} />
        Recent Investigations
      </h3>
      
      <div className="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
        {cases.map((c) => (
          <motion.button
            key={c.id}
            whileHover={{ x: 5 }}
            onClick={() => onSelect(c)}
            className="w-full p-3 bg-slate-900/40 hover:bg-slate-800/60 rounded-xl border border-slate-800/50 flex items-center justify-between transition-colors group"
          >
            <div className="text-left">
              <p className="text-xs font-bold text-slate-300">CASE #{c.id}</p>
              <p className="text-[9px] text-slate-500 font-medium uppercase tracking-tighter">
                {new Date(c.timestamp).toLocaleTimeString()} | {c.stage}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`w-1.5 h-1.5 rounded-full ${c.risk_score > 70 ? 'bg-red-500' : 'bg-green-500'}`} />
              <ChevronRight size={14} className="text-slate-600 group-hover:text-white transition-colors" />
            </div>
          </motion.button>
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-slate-800">
        <div className="flex items-center justify-between text-[10px] font-black text-slate-500 uppercase">
          <span>Global Audit Mode</span>
          <Scale size={14} className="text-accent-blue" />
        </div>
      </div>
    </div>
  );
};

export default CaseHistory;
