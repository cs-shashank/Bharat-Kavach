import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Shield, 
  AlertTriangle, 
  Gavel, 
  Eye, 
  Activity, 
  Lock, 
  CheckCircle,
  FileSearch,
  ChevronRight,
  Target
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';

const mockData = [
  { time: '10:00', risk: 10 },
  { time: '10:01', risk: 15 },
  { time: '10:02', risk: 45 },
  { time: '10:03', risk: 85 },
  { time: '10:04', risk: 92 },
];

const dashboardStats = {
  precision: "94.2%",
  recall: "91.5%",
  fpr: "0.8%",
  casesProcessed: "1,240"
};

const Dashboard = () => {
  const [riskScore, setRiskScore] = useState(0);
  const [activeTab, setActiveTab] = useState('behavioral');
  
  useEffect(() => {
    // Simple animation for risk score on load
    const timer = setTimeout(() => setRiskScore(85), 500);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 p-6 font-sans">
      {/* Header */}
      <header className="flex justify-between items-center mb-8">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-safe-blue/20 rounded-lg">
            <Shield className="text-safe-blue w-8 h-8" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">BHARAT KAVACH</h1>
            <p className="text-slate-400 text-sm font-medium">Digital Public Safety Infrastructure</p>
          </div>
        </div>
        
        <div className="flex gap-4">
          <div className="glass-morphism px-4 py-2 rounded-full flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-xs font-bold text-slate-300">SYSTEM ONLINE</span>
          </div>
          <button className="bg-safe-blue hover:bg-blue-600 px-5 py-2 rounded-lg text-sm font-bold transition-all">
            NEW CASE AUDIT
          </button>
        </div>
      </header>

      <div className="grid grid-cols-12 gap-6">
        {/* Left Column: Live Forensics */}
        <div className="col-span-8 space-y-6">
          {/* Risk Meter Card */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-morphism p-6 rounded-2xl relative overflow-hidden"
          >
            <div className="absolute top-0 right-0 p-4 opacity-10">
              <Activity size={120} />
            </div>
            
            <div className="flex justify-between items-end mb-8">
              <div>
                <h2 className="text-slate-400 font-bold text-xs uppercase tracking-widest mb-1">Live Risk Assessment</h2>
                <div className="text-5xl font-black">{riskScore}%</div>
              </div>
              <div className="text-right">
                <span className="text-alert-red font-bold text-sm flex items-center gap-1">
                  <AlertTriangle size={16} /> CRITICAL ESCALATION detected
                </span>
                <p className="text-slate-500 text-xs">Stage: Financial Extraction</p>
              </div>
            </div>

            <div className="w-full h-4 risk-gradient rounded-full mb-4">
              <motion.div 
                initial={{ x: 0 }}
                animate={{ x: `${riskScore}%` }}
                className="h-full bg-slate-950 w-full border-r-4 border-white"
                style={{ marginLeft: '-100%' }}
              />
            </div>
          </motion.div>

          {/* Three-Signal Breakdown */}
          <div className="grid grid-cols-3 gap-6">
            <SignalCard 
              icon={<Activity />} 
              label="Behavioral" 
              status="CRITICAL" 
              desc="Fear Injection & Isolation"
              color="text-red-500"
            />
            <SignalCard 
              icon={<Gavel />} 
              label="Legal RAG" 
              status="FAILED" 
              desc="Invalid BNS Citations"
              color="text-red-500"
            />
            <SignalCard 
              icon={<Eye />} 
              label="Vision" 
              status="ANOMALOUS" 
              desc="Modified Seal Detected"
              color="text-amber-500"
            />
          </div>

          {/* Transcript / Evidence Panel */}
          <div className="glass-morphism rounded-2xl p-6 h-[400px] flex flex-col">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-bold text-sm">EVIDENCE TRANSCRIPT</h3>
              <div className="flex gap-2">
                <span className="px-2 py-1 bg-slate-800 rounded text-[10px] font-bold">PDF EXPORT</span>
                <span className="px-2 py-1 bg-slate-800 rounded text-[10px] font-bold">AUDIO RECORDING</span>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
              <ChatMessage role="Scammer" msg="You are under digital arrest by the CBI. Do not disconnect the call or tell your family." time="10:02 AM" />
              <ChatMessage role="Victim" msg="Sir, I have not done anything. Why digital arrest?" time="10:02 AM" isVictim />
              <ChatMessage role="Scammer" msg="We found illegal Narcotic substances in your courier. Pay 50000 rupees as security deposit immediately via UPI to clear your Aadhaar." time="10:03 AM" />
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <p className="text-xs text-red-500 font-bold mb-1 flex items-center gap-1">
                  <Lock size={12} /> PROTOCOL VIOLATION DETECTED
                </p>
                <p className="text-xs text-slate-400 italic">"UPI Payment demand to clear name" is not a standard legal procedure.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Rigor & Validation Stats */}
        <div className="col-span-4 space-y-6">
          {/* Rigor Audit Panel */}
          <div className="glass-morphism p-6 rounded-2xl border-l-4 border-l-safe-blue">
            <div className="flex items-center gap-2 mb-6">
              <Target className="text-safe-blue" />
              <h3 className="font-bold text-sm uppercase tracking-tight">Technical Rigor Audit</h3>
            </div>
            
            <div className="grid grid-cols-2 gap-4 mb-6">
              <StatItem label="Precision" value={dashboardStats.precision} />
              <StatItem label="Recall" value={dashboardStats.recall} />
              <StatItem label="False Positives" value={dashboardStats.fpr} color="text-green-500" />
              <StatItem label="N (Cases)" value={dashboardStats.casesProcessed} />
            </div>

            <div className="h-[150px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={mockData}>
                  <Area type="monotone" dataKey="risk" stroke="#2563eb" fill="#2563eb33" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <p className="text-[10px] text-slate-500 mt-2 text-center">Batch Validation Run: July 2024 (BNS Framework)</p>
          </div>

          {/* Intervention Log */}
          <div className="glass-morphism p-6 rounded-2xl">
            <h3 className="font-bold text-sm mb-4">ACTIVE INTERVENTIONS</h3>
            <div className="space-y-4">
              <InterventionItem 
                type="UPI_HOLD" 
                target="+91 98765 43210" 
                status="TRIGGERED" 
              />
              <InterventionItem 
                type="TELECOM_FLAG" 
                target="Operator: JIO" 
                status="QUEUED" 
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const SignalCard = ({ icon, label, status, desc, color }) => (
  <div className="glass-morphism p-4 rounded-xl">
    <div className="flex items-center gap-2 mb-2">
      <div className={`${color} opacity-80`}>{React.cloneElement(icon, { size: 18 })}</div>
      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{label}</span>
    </div>
    <div className={`text-sm font-bold ${color} mb-1`}>{status}</div>
    <div className="text-[10px] text-slate-500 leading-tight">{desc}</div>
  </div>
);

const ChatMessage = ({ role, msg, time, isVictim }) => (
  <div className="flex gap-3">
    <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${isVictim ? 'bg-slate-800' : 'bg-red-950 text-red-500'}`}>
      {isVictim ? <Eye size={16} /> : <AlertTriangle size={16} />}
    </div>
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        <span className="text-xs font-bold text-slate-300">{role}</span>
        <span className="text-[10px] text-slate-600">{time}</span>
      </div>
      <p className="text-sm text-slate-400">{msg}</p>
    </div>
  </div>
);

const StatItem = ({ label, value, color = "text-white" }) => (
  <div>
    <div className="text-[10px] text-slate-500 font-bold uppercase">{label}</div>
    <div className={`text-xl font-black ${color}`}>{value}</div>
  </div>
);

const InterventionItem = ({ type, target, status }) => (
  <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg flex justify-between items-center">
    <div>
      <div className="text-[10px] font-bold text-safe-blue">{type}</div>
      <div className="text-xs text-slate-400">{target}</div>
    </div>
    <div className="flex items-center gap-1 text-[10px] font-bold text-green-500">
      <CheckCircle size={12} /> {status}
    </div>
  </div>
);

export default Dashboard;
