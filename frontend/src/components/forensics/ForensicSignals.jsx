import React from 'react';
import { motion } from 'framer-motion';
import { Search, Gavel, Eye, FileCheck } from 'lucide-react';

const SignalIndicator = ({ icon: Icon, label, value, status, delay }) => (
  <motion.div 
    initial={{ opacity: 0, x: -20 }}
    animate={{ opacity: 1, x: 0 }}
    transition={{ delay }}
    className="flex items-center gap-4 p-3 bg-slate-900/60 rounded-xl border border-slate-800/50"
  >
    <div className={`p-2 rounded-lg ${status === 'Alert' ? 'bg-red-500/10 text-red-500' : 'bg-blue-500/10 text-blue-500'}`}>
      <Icon size={18} />
    </div>
    <div className="flex-1">
      <div className="flex justify-between items-center mb-1">
        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{label}</span>
        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${status === 'Alert' ? 'bg-red-500/20 text-red-500' : 'bg-green-500/20 text-green-500'}`}>
          {status}
        </span>
      </div>
      <div className="w-full bg-slate-800 h-1 rounded-full overflow-hidden">
        <motion.div 
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          className={`h-full ${status === 'Alert' ? 'bg-red-500' : 'bg-blue-500'}`}
          transition={{ duration: 1, delay: delay + 0.5 }}
        />
      </div>
    </div>
  </motion.div>
);

const ForensicSignals = ({ signals }) => {
  return (
    <div className="glass-card p-6 space-y-4">
      <h3 className="text-xs font-bold text-slate-500 tracking-widest uppercase mb-4">Forensic Signal Streams</h3>
      <div className="flex flex-col gap-3">
        <SignalIndicator 
          icon={Search} 
          label="Behavioral Arc" 
          value={signals.behavioral || 0} 
          status={signals.behavioral > 60 ? 'Alert' : 'Normal'} 
          delay={0.1}
        />
        <SignalIndicator 
          icon={Gavel} 
          label="Legal Grounding" 
          value={signals.legal || 0} 
          status={signals.legal < 50 ? 'Alert' : 'Secure'} 
          delay={0.2}
        />
        <SignalIndicator 
          icon={Eye} 
          label="Vision Integrity" 
          value={signals.vision || 0} 
          status={signals.vision < 40 ? 'Alert' : 'Secure'} 
          delay={0.3}
        />
        <SignalIndicator 
          icon={FileCheck} 
          label="Protocol Compliance" 
          value={signals.protocol || 0} 
          status={signals.protocol < 100 ? 'Alert' : 'Secure'} 
          delay={0.4}
        />
      </div>
    </div>
  );
};

export default ForensicSignals;
