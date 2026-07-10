import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileSearch, Upload, Loader2, AlertTriangle, ShieldAlert, ShieldCheck } from 'lucide-react';

const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'application/pdf'];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

const DocumentPanel = () => {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (!selected) return;

    if (!ALLOWED_MIME_TYPES.includes(selected.type)) {
      setError('Unsupported file type. Please upload a JPEG, PNG, or PDF.');
      setFile(null);
      e.target.value = '';
      return;
    }

    if (selected.size > MAX_FILE_SIZE) {
      setError('File too large. Maximum 10 MB.');
      setFile(null);
      e.target.value = '';
      return;
    }

    setFile(selected);
    setError(null);
  };

  const handleSubmit = async () => {
    if (!file) {
      setError('Please select a document to analyze');
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

      const response = await fetch('http://localhost:8000/analyze-document', {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch {
      clearTimeout(timeoutId);
      setError('Document analysis failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const isHighForgery =
    result &&
    result.verdict?.includes('Fake') &&
    result.confidence_score >= 0.75;

  return (
    <div className="glass-card p-6 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <FileSearch size={16} className="text-accent-blue" />
        <h3 className="text-xs font-bold text-slate-500 tracking-widest uppercase">
          Document Forensics
        </h3>
      </div>

      {/* File Input */}
      <div className="flex flex-col gap-2">
        <label className="flex flex-col items-center justify-center gap-2 p-4 border-2 border-dashed border-slate-700 rounded-xl cursor-pointer hover:border-accent-blue/50 hover:bg-slate-800/30 transition-all">
          <Upload size={20} className="text-slate-500" />
          <span className="text-xs text-slate-400 font-medium">
            {file ? file.name : 'Click to upload document'}
          </span>
          <span className="text-[10px] text-slate-600 font-medium uppercase tracking-wide">
            JPEG · PNG · PDF · Max 10 MB
          </span>
          <input
            type="file"
            accept="image/jpeg,image/png,application/pdf"
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
            ANALYZING...
          </>
        ) : (
          <>
            <FileSearch size={16} />
            ANALYZE DOCUMENT
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
            className={`flex flex-col gap-3 p-4 rounded-xl border ${
              isHighForgery
                ? 'bg-red-500/10 border-red-500'
                : 'bg-slate-900/60 border-slate-700/50'
            }`}
          >
            {/* High Forgery Alert */}
            {isHighForgery && (
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="flex items-center justify-center gap-2 p-2 bg-red-500/20 border border-red-500/50 rounded-lg"
              >
                <ShieldAlert size={14} className="text-red-400" />
                <span className="text-xs font-black text-red-400 uppercase tracking-wider">
                  High Forgery Confidence
                </span>
              </motion.div>
            )}

            {/* Verdict */}
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">
                Verdict
              </span>
              <span
                className={`text-xs font-bold flex items-center gap-1 ${
                  isHighForgery ? 'text-red-400' : 'text-slate-200'
                }`}
              >
                {!isHighForgery && <ShieldCheck size={12} className="text-green-400" />}
                {isHighForgery && <ShieldAlert size={12} className="text-red-400" />}
                {result.verdict}
              </span>
            </div>

            {/* Confidence Score */}
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">
                Confidence
              </span>
              <span className="text-xs font-bold text-slate-200">
                {Math.round(result.confidence_score * 100)}%
              </span>
            </div>

            {/* Explanation */}
            {result.explanation && (
              <div className="pt-1 border-t border-slate-700/50">
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">
                  Explanation
                </p>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {result.explanation}
                </p>
              </div>
            )}

            {/* Forensic Signals */}
            {result.forensic_signals &&
              Object.keys(result.forensic_signals).length > 0 && (
                <div className="pt-1 border-t border-slate-700/50 flex flex-col gap-2">
                  <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">
                    Forensic Signals
                  </p>
                  {Object.entries(result.forensic_signals).map(([key, value]) => (
                    <div key={key} className="flex flex-col gap-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-slate-400 capitalize">
                          {key.replace(/_/g, ' ')}
                        </span>
                        <span className="text-[10px] font-bold text-slate-300">
                          {Math.round(value * 100)}%
                        </span>
                      </div>
                      <div className="h-1.5 bg-slate-700/60 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-accent-blue rounded-full transition-all duration-500"
                          style={{ width: `${Math.round(value * 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default DocumentPanel;
