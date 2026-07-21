import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Banknote, Upload, Loader2, AlertTriangle, CheckCircle, ShieldAlert, Shield, Clock } from 'lucide-react';
import { API_BASE } from '../../config.js';

const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png'];

const CurrencyPanel = () => {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [rateLimited, setRateLimited] = useState(false);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (!selected) return;

    if (!ALLOWED_MIME_TYPES.includes(selected.type)) {
      setError('Unsupported file type. Please upload a JPEG or PNG image.');
      setFile(null);
      e.target.value = '';
      return;
    }

    setFile(selected);
    setError(null);
  };

  const handleSubmit = async () => {
    if (!file) {
      setError('Please select a currency image to verify');
      return;
    }

    setLoading(true);
    setResult(null);
    setError(null);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/analyze-currency`, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.status === 429) { setRateLimited(true); return; }
      if (!response.ok) { throw new Error(`HTTP ${response.status}`); }

      const data = await response.json();
      setResult(data);
    } catch {
      clearTimeout(timeoutId);
      setError('Currency verification failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-card p-6 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Banknote size={16} className="text-accent-blue" />
        <h3 className="text-xs font-bold text-slate-500 tracking-widest uppercase">
          Currency Verification
        </h3>
      </div>

      {/* File Input */}
      <div className="flex flex-col gap-2">
        <label className="flex flex-col items-center justify-center gap-2 p-4 border-2 border-dashed border-slate-700 rounded-xl cursor-pointer hover:border-accent-blue/50 hover:bg-slate-800/30 transition-all">
          <Upload size={20} className="text-slate-500" />
          <span className="text-xs text-slate-400 font-medium">
            {file ? file.name : 'Click to upload JPEG or PNG'}
          </span>
          <span className="text-[10px] text-slate-600 font-medium uppercase tracking-wide">
            JPEG · PNG only
          </span>
          <input
            type="file"
            accept="image/jpeg,image/png"
            onChange={handleFileChange}
            className="hidden"
          />
        </label>
      </div>

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
            VERIFYING...
          </>
        ) : (
          <>
            <Shield size={16} />
            VERIFY NOTE
          </>
        )}
      </button>

      {/* Result */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            className="flex flex-col gap-3 p-4 bg-slate-900/60 border border-slate-700/50 rounded-xl"
          >
            {/* Note Type */}
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">
                Note Type
              </span>
              <span className="text-xs font-bold text-slate-200">
                {result.note_type}
              </span>
            </div>

            {/* Security Thread */}
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">
                Security Thread
              </span>
              <span className={`text-xs font-bold flex items-center gap-1 ${result.signals?.thread_detected ? 'text-green-400' : 'text-red-400'}`}>
                {result.signals?.thread_detected ? (
                  <>
                    <CheckCircle size={12} />
                    Detected
                  </>
                ) : (
                  <>
                    <AlertTriangle size={12} />
                    Not Detected
                  </>
                )}
              </span>
            </div>

            {/* Reason (if present) */}
            {result.signals?.reason && (
              <div className="pt-1 border-t border-slate-700/50">
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">
                  Reason
                </p>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {result.signals.reason}
                </p>
              </div>
            )}

            {/* Suspicion Badge */}
            <div className="pt-1">
              {result.signals?.is_suspicious === true && (
                <motion.div
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  className="flex items-center justify-center gap-2 p-3 bg-red-500/15 border border-red-500/40 rounded-xl"
                >
                  <ShieldAlert size={16} className="text-red-400" />
                  <span className="text-xs font-black text-red-400 uppercase tracking-wider">
                    Suspicious Note Detected
                  </span>
                </motion.div>
              )}
              {result.signals?.is_suspicious === false && (
                <motion.div
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  className="flex items-center justify-center gap-2 p-3 bg-green-500/15 border border-green-500/40 rounded-xl"
                >
                  <CheckCircle size={16} className="text-green-400" />
                  <span className="text-xs font-black text-green-400 uppercase tracking-wider">
                    Note Appears Genuine
                  </span>
                </motion.div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default CurrencyPanel;
