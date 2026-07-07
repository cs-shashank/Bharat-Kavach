import React from 'react';
import { Map, Pin, Crosshair } from 'lucide-react';
import { motion } from 'framer-motion';

const CrimeMap = () => {
  const hotspots = [
    { id: 1, x: 120, y: 80, strength: 'High', label: 'Tech Park District' },
    { id: 2, x: 250, y: 150, strength: 'Med', label: 'Financial Corridor' },
    { id: 3, x: 180, y: 220, strength: 'Critical', label: 'Old City Hub' }
  ];

  return (
    <div className="glass-card p-6 h-full flex flex-col">
      <div className="w-full flex justify-between items-center mb-6">
        <div className="flex items-center gap-2">
          <Map size={16} className="text-accent-gold" />
          <h3 className="text-xs font-bold text-slate-500 tracking-widest uppercase">Geospatial Intelligence Layer</h3>
        </div>
        <span className="text-[10px] font-bold text-slate-400">NODE: ACTIVE_CITY_SCAN</span>
      </div>

      <div className="flex-1 relative bg-slate-900/50 rounded-2xl border border-slate-800 flex items-center justify-center overflow-hidden">
        {/* Simplified SVG Map of a District / Grid */}
        <svg viewBox="0 0 400 300" className="w-full h-full opacity-30">
          <path d="M 50 50 L 350 50 L 350 250 L 50 250 Z" fill="none" stroke="#334155" strokeWidth="2" strokeDasharray="4 4" />
          <path d="M 50 150 L 350 150 M 200 50 L 200 250" stroke="#334155" strokeWidth="1" />
        </svg>

        {/* Dynamic Hotspots */}
        {hotspots.map((spot, idx) => (
          <motion.div
            key={spot.id}
            initial={{ scale: 0 }}
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ repeat: Infinity, duration: 2, delay: idx * 0.5 }}
            className="absolute p-2"
            style={{ left: spot.x, top: spot.y }}
          >
            <div className={`relative flex items-center justify-center`}>
              <div className={`absolute w-8 h-8 rounded-full ${spot.strength === 'Critical' ? 'bg-red-500/20' : 'bg-orange-500/20'} animate-ping`} />
              <Pin size={20} className={spot.strength === 'Critical' ? 'text-red-500' : 'text-orange-500'} />
            </div>
            
            {/* Tooltip Simulation */}
            <div className="absolute top-8 left-1/2 -translate-x-1/2 bg-slate-900 px-2 py-1 rounded border border-slate-800 whitespace-nowrap">
              <p className="text-[8px] font-black text-white uppercase">{spot.label}</p>
              <p className="text-[7px] text-slate-400 uppercase">{spot.strength} INCIDENT DENSITY</p>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="mt-4 flex items-center justify-between text-[10px] font-bold text-slate-500">
        <div className="flex items-center gap-2">
          <Crosshair size={12} />
          <span>Real-time Patrol Prioritization Active</span>
        </div>
        <button className="text-accent-blue hover:underline">EXTRACT GEOSPATIAL LOGS</button>
      </div>
    </div>
  );
};

export default CrimeMap;
