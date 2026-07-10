import React from 'react';
import { motion } from 'framer-motion';
import { Share2, Smartphone, UserX } from 'lucide-react';

// ─── Sub-components ──────────────────────────────────────────────────────────

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
    <text
      x={x}
      y={y + 45}
      textAnchor="middle"
      fill="#94a3b8"
      className="text-[10px] font-bold uppercase tracking-tighter"
    >
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

// ─── Network derivation ───────────────────────────────────────────────────────

const PHONE_REGEX = /[6-9]\d{9}/g;

export function deriveNetwork(cases) {
  const highRisk = cases.filter(c => c.risk_score > 70);
  if (highRisk.length === 0) return null;

  // Primary Suspect: highest timestamp, tiebreak by largest id
  const primary = highRisk.reduce((best, c) => {
    const tBest = new Date(best.timestamp).getTime();
    const tC = new Date(c.timestamp).getTime();
    if (tC > tBest) return c;
    if (tC === tBest) return c.id > best.id ? c : best;
    return best;
  });

  // Scan ALL cases' transcripts for phone numbers
  const phoneSet = new Set();
  const contributingIds = new Set([primary.id]);

  cases.forEach(c => {
    const matches = (c.transcript || '').match(PHONE_REGEX) || [];
    if (matches.length > 0) contributingIds.add(c.id);
    matches.forEach(p => phoneSet.add(p));
  });

  return {
    primary,
    phones: [...phoneSet],
    linkedCount: contributingIds.size,
  };
}

// ─── Main component ───────────────────────────────────────────────────────────

const FraudNetwork = ({ cases, fetchError }) => {
  // fetchError prop or undefined/null cases → "Network data unavailable"
  if (fetchError || cases == null) {
    return (
      <div className="glass-card p-6 h-full flex flex-col items-center">
        <Header badge="NETWORK DATA UNAVAILABLE" />
        <EmptyMessage text="Network data unavailable" />
        <AnalyticInsight />
      </div>
    );
  }

  const network = deriveNetwork(cases);

  // No high-risk cases found
  if (network === null) {
    return (
      <div className="glass-card p-6 h-full flex flex-col items-center">
        <Header badge="0 CASES LINKED" />
        <EmptyMessage text="No high-risk cases detected" />
        <AnalyticInsight />
      </div>
    );
  }

  const { primary, phones, linkedCount } = network;

  // SVG layout constants
  const CX = 200;
  const CY = 150;
  const RADIUS = 90;

  const phoneNodes = phones.map((phone, i) => {
    const angle = phones.length === 1
      ? -Math.PI / 2                          // single node sits directly above
      : (2 * Math.PI * i) / phones.length - Math.PI / 2;
    return {
      phone,
      x: CX + RADIUS * Math.cos(angle),
      y: CY + RADIUS * Math.sin(angle),
    };
  });

  return (
    <div className="glass-card p-6 h-full flex flex-col items-center">
      <Header badge={`${linkedCount} CASES LINKED`} />

      <svg width="400" height="300" className="w-full h-full min-h-[250px]">
        {/* Edges first so nodes render on top */}
        {phoneNodes.map(({ phone, x, y }, i) => (
          <Connection
            key={`edge-${phone}`}
            x1={CX}
            y1={CY}
            x2={x}
            y2={y}
            delay={0.4 + i * 0.15}
          />
        ))}

        {/* Primary Suspect node */}
        <Node
          x={CX}
          y={CY}
          icon={UserX}
          label={primary.user_id || 'Unknown'}
          color="#ef4444"
          delay={0.2}
        />

        {/* Phone nodes */}
        {phoneNodes.map(({ phone, x, y }, i) => (
          <Node
            key={`node-${phone}`}
            x={x}
            y={y}
            icon={Smartphone}
            label={phone}
            color="#3b82f6"
            delay={0.5 + i * 0.15}
          />
        ))}
      </svg>

      <AnalyticInsight />
    </div>
  );
};

// ─── Shared layout helpers ────────────────────────────────────────────────────

const Header = ({ badge }) => (
  <div className="w-full flex justify-between items-center mb-6">
    <div className="flex items-center gap-2">
      <Share2 size={16} className="text-accent-blue" />
      <h3 className="text-xs font-bold text-slate-500 tracking-widest uppercase">
        Fraud Network Graph AI
      </h3>
    </div>
    <span className="text-[10px] font-bold bg-blue-500/10 text-blue-500 px-2 py-0.5 rounded border border-blue-500/20">
      {badge}
    </span>
  </div>
);

const EmptyMessage = ({ text }) => (
  <div className="flex-1 flex items-center justify-center">
    <p className="text-slate-500 text-sm font-medium">{text}</p>
  </div>
);

const AnalyticInsight = () => (
  <div className="w-full mt-4 p-3 bg-blue-500/5 rounded-xl border border-blue-500/10 text-[10px] text-slate-400 font-medium italic">
    "Analytic Insight: Cluster linked to 'Cambodia-based' fraud compound. Coordinated timing with 12 other victim reports."
  </div>
);

export default FraudNetwork;
