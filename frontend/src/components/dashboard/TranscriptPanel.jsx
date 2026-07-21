import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, Loader2, AlertTriangle, ScanSearch, Clock } from 'lucide-react';
import { API_BASE } from '../../config.js';

// Simple in-memory cache: transcript text → analysis result
// Prevents burning API quota when the same transcript is submitted twice
const _analysisCache = new Map();

const TranscriptPanel = ({ onResult, onSubmit }) => {
  const [transcript, setTranscript] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [rateLimited, setRateLimited] = useState(false);

  const DEMO_CITIES = ['Delhi', 'Mumbai', 'Bangalore', 'Chennai', 'Kolkata', 'Hyderabad', 'Pune', 'Ahmedabad'];

  const handleSubmit = async () => {
    if (!transcript.trim()) {
      setError('Transcript cannot be empty');
      return;
    }

    // Serve from cache if available — saves API quota
    const cacheKey = transcript.trim();
    if (_analysisCache.has(cacheKey)) {
      onResult(_analysisCache.get(cacheKey));
      return;
    }

    if (onSubmit) onSubmit(transcript);

    setLoading(true);
    setError(null);
    setRateLimited(false);

    // Rotate through cities so the crime map shows hotspots across India
    const city = DEMO_CITIES[Math.floor(Math.random() * DEMO_CITIES.length)];

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000);

    try {
      const response = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcript, user_id: 'OFFICER_001', city }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Graceful 429 handling — never show a broken screen
      if (response.status === 429) {
        setRateLimited(true);
        return;
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      _analysisCache.set(cacheKey, data); // cache for quota protection
      onResult(data);
      setError(null);
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        setError('Request timed out. Please try again.');
      } else {
        setError('Analysis failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-card p-6 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <FileText size={16} className="text-accent-blue" />
        <h3 className="text-xs font-bold text-slate-500 tracking-widest uppercase">
          Live Transcript Analysis
        </h3>
      </div>

      {/* Textarea */}
      <textarea
        value={transcript}
        onChange={(e) => setTranscript(e.target.value)}
        maxLength={10000}
        placeholder="Paste conversation transcript here..."
        rows={6}
        className="w-full bg-slate-900/60 border border-slate-700/50 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder:text-slate-600 resize-none focus:outline-none focus:ring-1 focus:ring-accent-blue/50 focus:border-accent-blue/50 transition-all custom-scrollbar"
      />

      {/* Character count */}
      <p className="text-[10px] text-slate-600 font-medium text-right -mt-2">
        {transcript.length.toLocaleString()} / 10,000
      </p>

      {/* Rate limit banner — shown instead of error when API quota is hit */}
      <AnimatePresence>
        {rateLimited && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="flex items-center gap-2 p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl"
          >
            <Clock size={14} className="text-amber-400 shrink-0" />
            <p className="text-xs text-amber-400 font-medium">
              High demand — AI engine is busy. Please wait a moment and try again.
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error Message */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-xl"
          >
            <AlertTriangle size={14} className="text-red-400 shrink-0" />
            <p className="text-xs text-red-400 font-medium">{error}</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Submit Button */}
      <button
        onClick={handleSubmit}
        disabled={loading}
        className="flex items-center justify-center gap-2 bg-accent-blue hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2.5 rounded-xl text-sm font-bold transition-all shadow-lg shadow-blue-500/20"
      >
        {loading ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            ANALYZING...
          </>
        ) : (
          <>
            <ScanSearch size={16} />
            ANALYZE
          </>
        )}
      </button>
    </div>
  );
};

export default TranscriptPanel;
