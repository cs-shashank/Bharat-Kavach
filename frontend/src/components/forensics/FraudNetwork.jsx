import React from 'react';
import { motion } from 'framer-motion';
import { Share2, Smartphone, Landmark, UserX } from 'lucide-react';

const Node = ({ x, y, icon: Icon, label, color, delay }) => (
  <motion.g
    initial={{ opacity: 0, scale: 0 }}
    animate={{ opacity: 1, scale: 1 }}
    transition={{ delay, type: 'spring' }}
  >
    <circle cx={x} cy={y} r="25" fill="#0f172a" stroke={color} strokeWidth="2" className="drop-shadow-lg" />
    <foreignObject x={x - 12} y={y - 12} width="24" height="24">
      <Icon size={24} color={color} />
    </foreignObject>
    <text x={x} y={y + 45} textAnchor="middle" fill="#94a3b8" className="text-[10px] font-bold uppercase tracking-tighter">
      {label}
    </text>
  </motion.g>
);

const Connection = ({ x1, y1, x2, y2, delay }) => (
  <motion.line
    x1={x1}
    y1={y1}
    x2={x2}
    y2={y2}
    stroke="#334155"
    strokeWidth="1"
    initial={{ pathLength: 0 }}
    animate={{ pathLength: 1 }}
    transition={{ delay, duration: 1.5 }}
  />
);

const FraudNetwork = () => {
  return (
    <div className="glass-card p-6 h-full flex flex-col items-center">
      <div className="w-full flex justify-between items-center mb-6">
        <div className="flex items-center gap-2">
          <Share2 size={16} className="text-accent-blue" />
          <h3 className="text-xs font-bold text-slate-500 tracking-widest uppercase">Fraud Network Graph AI</h3>
        </div>
        <span className="text-[10px] font-bold bg-blue-500/10 text-blue-500 px-2 py-0.5 rounded border border-blue-500/20">
          CLUSTERING ACTIVE
        </span>
      </div>

      <svg width="400" height="300" className="w-full h-full min-h-[250px]">
        {/* Connections */}
        <Connection x1="200" y1="150" x2="100" y2="80" delay={0.5} />
        <Connection x1="200" y1="150" x2="300" y2="80" delay={0.7} />
        <Connection x1="100" y1="80" x2="50" y2="200" delay={0.9} />
        <Connection x1="300" y1="80" x2="350" y2="200" delay={1.1} />
        <Connection x1="200" y1="150" x2="200" y2="250" delay={1.3} />

        {/* Nodes */}
        <Node x={200} y={150} icon={UserX} label="Primary Suspect" color="#ef4444" delay={0.2} />
        <Node x={100} y={80} icon={Smartphone} label="+91-98XXX" color="#3b82f6" delay={0.4} />
        <Node x={300} y={80} icon={Smartphone} label="+91-87XXX" color="#3b82f6" delay={0.6} />
        <Node x={50} y={200} icon={Landmark} label="Mule_Acct_1" color="#f59e0b" delay={0.8} />
        <Node x={350} y={200} icon={Landmark} label="Mule_Acct_2" color="#f59e0b" delay={1.0} />
        <Node x={200} y={250} icon={Smartphone} label="Spoof_App_X" color="#94a3b8" delay={1.2} />
      </svg>

      <div className="w-full mt-4 p-3 bg-blue-500/5 rounded-xl border border-blue-500/10 text-[10px] text-slate-400 font-medium italic">
        "Analytic Insight: Cluster linked to 'Cambodia-based' fraud compound. Coordinated timing with 12 other victim reports."
      </div>
    </div>
  );
};

export default FraudNetwork;
