import React, { useState, useEffect } from 'react';
import RiskMeter from '../forensics/RiskMeter';
import ForensicSignals from '../forensics/ForensicSignals';
import LegalAudit from '../forensics/LegalAudit';
import InterventionLog from '../forensics/InterventionLog';
import FraudNetwork from '../forensics/FraudNetwork';
import CrimeMap from '../forensics/CrimeMap';
import CaseHistory from './CaseHistory';
import { Shield, Activity, Users, Map as MapIcon, Bell, Download, ShieldAlert } from 'lucide-react';

const Dashboard = () => {
  const [caseData, setCaseData] = useState({
    score: 0,
    stage: 'Awaiting Stream',
    signals: { behavioral: 0, legal: 100, vision: 100, protocol: 100 },
    findings: [],
    interventions: [],
    history: []
  });

  // On Mount: Fetch historical cases
  useEffect(() => {
    const fetchCases = async () => {
      try {
        const response = await fetch('http://localhost:8000/cases');
        const data = await response.json();
        if (data.length > 0) {
          const latest = data[0];
          setCaseData(prev => ({
            ...prev,
            score: latest.risk_score,
            stage: latest.stage,
            findings: latest.legal_citations,
            interventions: latest.interventions || [],
            history: data
          }));
        }
      } catch (error) {
        console.error("Failed to fetch cases:", error);
      }
    };
    fetchCases();

    const clientId = "POLICE_NODE_" + Math.floor(Math.random() * 1000);
    const ws = new WebSocket(`ws://localhost:8000/ws/${clientId}`);

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'FORENSIC_UPDATE') {
        setCaseData(prev => ({
          ...prev,
          score: message.data.score,
          stage: message.data.stage,
          findings: message.data.findings,
          interventions: [
            ...prev.interventions,
            { type: 'FINANCIAL', action: 'UPI_HOLD', details: 'Transaction 9823X flagged for Digital Arrest pattern.', timestamp: '14:22:11' }
          ]
        }));
      }
    };

    return () => ws.close();
  }, []);

  return (
    <div className="flex bg-slate-950 min-h-screen">
      {/* Mini Sidebar */}
      <nav className="w-20 border-r border-slate-900 flex flex-col items-center py-8 gap-8">
        <div className="p-2 bg-accent-blue/20 rounded-xl">
          <Shield className="text-accent-blue" size={24} />
        </div>
        <div className="flex flex-col gap-6 text-slate-500">
          <Activity size={20} className="hover:text-white cursor-pointer" />
          <Map size={20} className="hover:text-white cursor-pointer" />
          <Users size={20} className="hover:text-white cursor-pointer" />
        </div>
        <div className="mt-auto">
          <Bell size={20} className="text-slate-500 hover:text-white cursor-pointer" />
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1 p-8 space-y-8 max-w-7xl mx-auto">
        {/* Header */}
        <header className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-black tracking-tight flex items-center gap-3">
              BHARAT KAVACH
              <span className="text-[10px] font-bold bg-accent-blue/10 text-accent-blue px-2 py-0.5 rounded border border-accent-blue/20">
                FORENSIC ENGINE v1.0
              </span>
            </h1>
            <p className="text-slate-500 text-sm font-medium mt-1">Law Enforcement Investigation Dashboard</p>
          </div>
          
          <div className="flex gap-4">
            <div className="glass-card px-4 py-2 flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-[10px] font-bold text-slate-400">NODE: DELHI_CENTRAL</span>
            </div>
            <button className="bg-accent-blue hover:bg-blue-600 px-6 py-2 rounded-xl text-sm font-bold transition-all shadow-lg shadow-blue-500/20 flex items-center gap-2">
              <Download size={16} />
              EXPORT INTELLIGENCE PACKAGE
            </button>
          </div>
        </header>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-12 gap-8">
          {/* Main Forensic Core & History */}
          <div className="col-span-12 lg:col-span-3 space-y-8">
            <RiskMeter score={caseData.score} stage={caseData.stage} />
            <div className="h-[400px]">
              <CaseHistory cases={caseData.history} onSelect={(c) => setCaseData(prev => ({...prev, score: c.risk_score, stage: c.stage, findings: c.legal_citations}))} />
            </div>
          </div>

          {/* Intelligence Visualizers */}
          <div className="col-span-12 lg:col-span-5 space-y-8">
            <div className="h-[350px]">
              <CrimeMap />
            </div>
            <div className="h-[350px]">
              <FraudNetwork />
            </div>
          </div>

          {/* Legal & Intervention Logs */}
          <div className="col-span-12 lg:col-span-4 space-y-8">
            <LegalAudit findings={caseData.findings} />
            <InterventionLog logs={caseData.interventions} />
          </div>
        </div>

        {/* Action Status Bar */}
        {caseData.score > 70 && (
          <div className="fixed bottom-8 right-8 left-28 translate-y-0">
            <div className="bg-red-500 p-4 rounded-2xl flex justify-between items-center shadow-2xl shadow-red-500/30">
              <div className="flex items-center gap-4 text-white">
                <AlertTriangle className="animate-bounce" />
                <div>
                  <p className="font-black text-sm uppercase">Automatic Intervention Triggered</p>
                  <p className="text-[10px] opacity-80 font-bold uppercase">Target Account: 987XXXX210 | Bank: SBI | Status: HOLD_QUEUED</p>
                </div>
              </div>
              <button className="bg-white text-red-600 px-4 py-2 rounded-lg text-xs font-black hover:bg-slate-100 transition-colors">
                VIEW KILL-SWITCH LOGS
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

// Mock Alert icon wrapper
const AlertTriangle = (props) => (
  <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-alert-triangle"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>
);

export default Dashboard;
