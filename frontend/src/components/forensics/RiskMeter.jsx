import React from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, ShieldCheck } from 'lucide-react';

const RiskMeter = ({ score, stage }) => {
  // Map score to color and label
  const getRiskStatus = (val) => {
    if (val < 30) return { color: 'text-green-500', bg: 'bg-green-500', label: 'LOW RISK' };
    if (val < 70) return { color: 'text-yellow-500', bg: 'bg-yellow-500', label: 'SUSPICIOUS' };
    return { color: 'text-red-500', bg: 'bg-red-500', label: 'CRITICAL THREAT' };
  };

  const status = getRiskStatus(score);

  return (
    <div className="glass-card p-6 flex flex-col items-center justify-center relative overflow-hidden">
      <div className="flex justify-between w-full mb-4 items-center">
        <h3 className="text-xs font-bold text-slate-500 tracking-widest uppercase">Live Risk Core</h3>
        <span className={`text-[10px] font-black px-2 py-0.5 rounded ${status.bg} text-slate-950`}>
          {status.label}
        </span>
      </div>

      {/* SVG Radial Meter */}
      <div className="relative w-48 h-48 flex items-center justify-center">
        <svg className="w-full h-full transform -rotate-90">
          <circle
            cx="96"
            cy="96"
            r="80"
            stroke="currentColor"
            strokeWidth="12"
            fill="transparent"
            className="text-slate-800"
          />
          <motion.circle
            cx="96"
            cy="96"
            r="80"
            stroke="currentColor"
            strokeWidth="12"
            fill="transparent"
            strokeDasharray={502.4}
            initial={{ strokeDashoffset: 502.4 }}
            animate={{ strokeDashoffset: 502.4 - (502.4 * score) / 100 }}
            className={status.color}
            transition={{ duration: 1.5, ease: "easeOut" }}
          />
        </svg>
        <div className="absolute flex flex-col items-center">
          <span className="text-4xl font-black">{score}%</span>
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-tight">{stage}</span>
        </div>
      </div>

      <div className="mt-6 flex items-center gap-2 text-xs text-slate-400 font-medium">
        {score > 70 ? (
          <AlertTriangle size={14} className="text-red-500 animate-pulse" />
        ) : (
          <ShieldCheck size={14} className="text-green-500" />
        )}
        <span>Escalation Phase: {stage || 'Monitoring...'}</span>
      </div>
    </div>
  );
};

export default RiskMeter;
