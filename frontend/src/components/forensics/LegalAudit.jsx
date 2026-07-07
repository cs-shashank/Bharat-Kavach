import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BookOpen, CheckCircle, XCircle } from 'lucide-react';

const LegalAudit = ({ findings }) => {
  return (
    <div className="glass-card p-6 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <BookOpen size={16} className="text-accent-blue" />
        <h3 className="text-xs font-bold text-slate-500 tracking-widest uppercase">Legal Context Audit (BNS 2024)</h3>
      </div>
      
      <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
        <AnimatePresence initial={false}>
          {findings.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-slate-600 italic text-sm">
              Waiting for legal claims to audit...
            </div>
          ) : (
            findings.map((finding, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className={`p-4 rounded-xl border ${finding.verdict === 'confirmed_false' ? 'bg-red-500/5 border-red-500/20' : 'bg-green-500/5 border-green-500/20'}`}
              >
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-black text-slate-300">CLAIM: "{finding.claim}"</span>
                  {finding.verdict === 'confirmed_false' ? (
                    <XCircle size={14} className="text-red-500" />
                  ) : (
                    <CheckCircle size={14} className="text-green-500" />
                  )}
                </div>
                <p className="text-xs text-slate-400 mb-2 leading-relaxed">
                  {finding.explanation}
                </p>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold px-1.5 py-0.5 bg-slate-800 rounded text-slate-400">
                    CITATION: {finding.citation || 'General Procedure'}
                  </span>
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default LegalAudit;
