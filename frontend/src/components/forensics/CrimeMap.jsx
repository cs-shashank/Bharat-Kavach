import React from 'react';
import { Map } from 'lucide-react';
import { motion } from 'framer-motion';

// SVG coordinate lookup table for major Indian cities
// Coordinates are within a 500×580 viewBox
const CITY_COORDS = {
  "Delhi":     { x: 220, y: 120 },
  "Mumbai":    { x: 130, y: 280 },
  "Bangalore": { x: 195, y: 390 },
  "Chennai":   { x: 250, y: 410 },
  "Kolkata":   { x: 340, y: 210 },
  "Hyderabad": { x: 220, y: 330 },
  "Pune":      { x: 145, y: 300 },
  "Ahmedabad": { x: 110, y: 200 },
};

/**
 * Groups cases by city, counting how many cases belong to each known city.
 * Cases with null/undefined/unknown city are skipped.
 * @param {Array} cases - array of case report objects
 * @returns {Object} e.g. { "Delhi": 3, "Mumbai": 1 }
 */
export function groupByCity(cases) {
  const groups = {};
  cases.forEach(c => {
    if (c.city && CITY_COORDS[c.city]) {
      groups[c.city] = (groups[c.city] || 0) + 1;
    }
  });
  return groups;
}

/**
 * Returns a color hex string based on case count thresholds.
 * @param {number} count
 * @returns {string} hex color
 */
export function pinColor(count) {
  if (count >= 5) return "#ef4444"; // red — Critical
  if (count >= 2) return "#f97316"; // orange — High
  return "#eab308";                  // yellow — Medium
}

// Simplified but recognizable India SVG outline path
// Drawn within a 500×580 viewBox, covering major coastline and state outlines
const INDIA_PATH = `
  M 230 30
  L 260 32
  L 285 38
  L 310 50
  L 325 65
  L 340 80
  L 355 90
  L 370 95
  L 385 100
  L 390 115
  L 395 125
  L 385 130
  L 375 140
  L 370 155
  L 375 165
  L 380 178
  L 370 185
  L 360 195
  L 355 205
  L 360 215
  L 365 225
  L 358 235
  L 350 240
  L 345 250
  L 340 255
  L 350 265
  L 355 275
  L 345 285
  L 330 290
  L 320 300
  L 310 310
  L 300 325
  L 290 340
  L 280 355
  L 270 370
  L 262 385
  L 255 400
  L 248 415
  L 242 430
  L 238 445
  L 234 460
  L 230 470
  L 226 460
  L 222 445
  L 218 430
  L 215 415
  L 210 400
  L 205 388
  L 198 375
  L 192 362
  L 186 350
  L 178 338
  L 168 325
  L 158 315
  L 148 305
  L 138 295
  L 128 285
  L 118 272
  L 110 260
  L 106 248
  L 108 238
  L 114 228
  L 120 218
  L 116 208
  L 108 200
  L 100 190
  L 96 178
  L 100 165
  L 108 155
  L 112 143
  L 108 132
  L 112 120
  L 120 110
  L 130 102
  L 140 95
  L 150 90
  L 158 82
  L 162 72
  L 168 60
  L 178 50
  L 192 42
  L 210 34
  Z
`;

// Kashmir / northern extension
const KASHMIR_PATH = `
  M 210 34
  L 192 42
  L 178 50
  L 168 60
  L 162 72
  L 158 82
  L 150 90
  L 155 78
  L 162 65
  L 170 52
  L 180 40
  L 192 32
  L 205 27
  L 218 25
  L 230 26
  L 230 30
`;

// Northeast India appendage
const NORTHEAST_PATH = `
  M 355 205
  L 365 195
  L 378 188
  L 390 182
  L 405 178
  L 418 175
  L 428 170
  L 435 162
  L 428 155
  L 418 148
  L 408 145
  L 395 148
  L 382 152
  L 370 155
  L 365 165
  L 370 175
  L 368 185
  L 360 195
  L 355 205
`;

// Sri Lanka (small island)
const SRI_LANKA_PATH = `
  M 255 450
  L 262 458
  L 265 468
  L 262 478
  L 256 482
  L 250 478
  L 247 468
  L 250 458
  Z
`;

const CrimeMap = ({ cases = [], fetchError = false }) => {
  const cityGroups = groupByCity(cases);
  const hasData = cases.length > 0;

  return (
    <div className="glass-card p-6 h-full flex flex-col">
      {/* Header */}
      <div className="w-full flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <Map size={16} className="text-accent-gold" />
          <h3 className="text-xs font-bold text-slate-500 tracking-widest uppercase">
            Geospatial Intelligence Layer
          </h3>
        </div>
        <span className="text-[10px] font-bold text-slate-400">INDIA: LIVE HOTSPOT SCAN</span>
      </div>

      {/* Map container */}
      <div className="flex-1 relative bg-slate-900/50 rounded-2xl border border-slate-800 overflow-hidden flex flex-col items-center justify-center">
        <svg
          viewBox="0 0 500 580"
          className="w-full h-full"
          style={{ maxHeight: '420px' }}
          aria-label="India crime hotspot map"
        >
          {/* India outline — base fill */}
          <path
            d={INDIA_PATH}
            fill="#0f172a"
            stroke="#334155"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          {/* Kashmir extension */}
          <path
            d={KASHMIR_PATH}
            fill="#0f172a"
            stroke="#334155"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          {/* Northeast appendage */}
          <path
            d={NORTHEAST_PATH}
            fill="#0f172a"
            stroke="#334155"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          {/* Sri Lanka */}
          <path
            d={SRI_LANKA_PATH}
            fill="#0f172a"
            stroke="#334155"
            strokeWidth="1"
            strokeLinejoin="round"
          />

          {/* Internal state boundary suggestions (light lines) */}
          {/* Rough east-west dividers */}
          <line x1="140" y1="165" x2="355" y2="165" stroke="#1e293b" strokeWidth="0.8" />
          <line x1="130" y1="230" x2="350" y2="230" stroke="#1e293b" strokeWidth="0.8" />
          <line x1="128" y1="295" x2="320" y2="295" stroke="#1e293b" strokeWidth="0.8" />
          {/* Rough north-south dividers */}
          <line x1="220" y1="60" x2="220" y2="290" stroke="#1e293b" strokeWidth="0.8" />
          <line x1="280" y1="90" x2="280" y2="300" stroke="#1e293b" strokeWidth="0.8" />

          {/* Hotspot pins — one per city with cases */}
          {Object.entries(cityGroups).map(([city, count]) => {
            const { x, y } = CITY_COORDS[city];
            const color = pinColor(count);

            return (
              <g key={city} role="img" aria-label={`${city}: ${count} case${count !== 1 ? 's' : ''}`}>
                {/* Pulse halo */}
                <motion.circle
                  cx={x}
                  cy={y}
                  r={6}
                  fill={color}
                  fillOpacity={0.3}
                  animate={{ r: [6, 16, 6], opacity: [0.6, 0, 0.6] }}
                  transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
                />
                {/* Solid pin */}
                <motion.circle
                  cx={x}
                  cy={y}
                  r={5}
                  fill={color}
                  stroke="#0f172a"
                  strokeWidth="1.5"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", stiffness: 300, damping: 20 }}
                />
                {/* City label */}
                <text
                  x={x + 8}
                  y={y - 8}
                  fill="#e2e8f0"
                  fontSize="9"
                  fontWeight="bold"
                  fontFamily="monospace"
                >
                  {city}
                </text>
                <text
                  x={x + 8}
                  y={y + 2}
                  fill={color}
                  fontSize="8"
                  fontFamily="monospace"
                >
                  {count} case{count !== 1 ? 's' : ''}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Status messages rendered below map */}
        {fetchError && (
          <p className="text-xs font-bold text-slate-400 tracking-widest text-center py-2">
            Data unavailable
          </p>
        )}
        {!fetchError && !hasData && (
          <p className="text-xs font-bold text-slate-400 tracking-widest text-center py-2">
            No incidents reported
          </p>
        )}
      </div>

      {/* Legend */}
      <div className="mt-3 flex items-center gap-4 text-[10px] font-bold text-slate-500">
        <div className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-full bg-[#ef4444]" />
          <span>Critical (5+)</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-full bg-[#f97316]" />
          <span>High (2–4)</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-full bg-[#eab308]" />
          <span>Medium (1)</span>
        </div>
      </div>
    </div>
  );
};

export default CrimeMap;
