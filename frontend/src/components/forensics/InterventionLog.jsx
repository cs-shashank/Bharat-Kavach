import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldAlert, Zap, Globe, Lock } from 'lucide-react';

const InterventionLog = ({ logs }) => {
  return (
    <div className="glass-card p-6 min-h-[300px]">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Zap size={16} className="text-accent-gold" />
          <h3 className="text-xs font-bold text-slate-500 tracking-widest uppercase">Active Intervention Log</h3>
        </div>
        <span className="text-[10px] font-bold text-slate-500 bg-slate-900 px-2 py-1 rounded">LIVE SECURE STREAM</span>
      </div>

      <div className="space-y-3">
        <AnimatePresence>
          {logs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-600 italic text-sm">
              Monitoring network for threats...
            </div>
          ) : (
            logs.map((log, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-start gap-4 p-3 bg-slate-900/40 rounded-xl border border-slate-800/30"
              >
                <div className={`p-2 rounded-lg ${log.type === 'FINANCIAL' ? 'bg-accent-gold/10 text-accent-gold' : 'bg-accent-blue/10 text-accent-blue'}`}>
                  {log.type === 'FINANCIAL' ? <Lock size={14} /> : <Globe size={14} />}
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-[10px] font-black text-slate-300 uppercase tracking-tighter">{log.action}</span>
                    <span className="text-[9px] text-slate-500 font-mono">{log.timestamp}</span>
                  </div>
                  <p className="text-[11px] text-slate-400 font-medium">
                    {log.details}
                  </p>
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default InterventionLog;
