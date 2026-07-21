import React, { useState, useEffect } from 'react';
import RiskMeter from '../forensics/RiskMeter';
import ForensicSignals from '../forensics/ForensicSignals';
import LegalAudit from '../forensics/LegalAudit';
import InterventionLog from '../forensics/InterventionLog';
import FraudNetwork from '../forensics/FraudNetwork';
import CrimeMap from '../forensics/CrimeMap';
import CaseHistory from './CaseHistory';
import TranscriptPanel from './TranscriptPanel';
import DocumentPanel from './DocumentPanel';
import CurrencyPanel from './CurrencyPanel';
import { Shield, Activity, Users, MapIcon, Bell, Download, ShieldAlert, AlertTriangle } from 'lucide-react';
import { API_BASE } from '../../config.js';

// Exported for testing — returns true if any finding has verdict === "confirmed_false"
export function hasFalseFindings(findings) {
  return Array.isArray(findings) && findings.some(f => f.verdict === 'confirmed_false');
}

const Dashboard = () => {
  const [caseData, setCaseData] = useState({
    id: null,
    transcript: "",
    score: 0,
    stage: 'Awaiting Stream',
    signals: { behavioral: 0, legal: 100, vision: 100, protocol: 100 },
    findings: [],
    interventions: [],
    history: []
  });

  const [toast, setToast] = useState(null);

  // On Mount: Fetch historical cases for map/network — do NOT overwrite active case state
  useEffect(() => {
    const fetchCases = async () => {
      try {
        const response = await fetch(`${API_BASE}/cases`);
        const data = await response.json();
        // Only populate history for CrimeMap and FraudNetwork — never auto-fill score/stage/findings
        setCaseData(prev => ({ ...prev, history: data }));
      } catch (error) {
        console.error("Failed to fetch cases:", error);
      }
    };
    fetchCases();

    const clientId = "POLICE_NODE_" + Math.floor(Math.random() * 1000);
    const ws = new WebSocket(`${API_BASE.replace('https://', 'wss://').replace('http://', 'ws://')}/ws/${clientId}`);

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'FORENSIC_UPDATE') {
        const findings = message.data.findings;
        setCaseData(prev => ({
          ...prev,
          id: message.data.id ?? prev.id,
          score: message.data.score,
          stage: message.data.stage,
          findings,
          signals: {
            behavioral: message.data.score,
            legal: hasFalseFindings(findings) ? 0 : 100,
            vision: prev.signals.vision,
            protocol: prev.signals.protocol,
          },
        }));
        // Re-fetch cases to refresh history for FraudNetwork and CrimeMap
        fetch(`${API_BASE}/cases`)
          .then(r => r.json())
          .then(data => setCaseData(prev => ({ ...prev, history: data })))
          .catch(err => console.error("Failed to refresh cases:", err));
      } else if (message.type === 'KILL_SWITCH_TRIGGERED') {
        setCaseData(prev => ({
          ...prev,
          interventions: [
            ...prev.interventions,
            {
              type: 'FINANCIAL',
              action: message.data.actions_taken[0],
              details: message.data.incident_id,
              timestamp: message.data.timestamp,
              incident_id: message.data.incident_id,
              actions_taken: message.data.actions_taken,
            }
          ]
        }));
      }
    };

    return () => ws.close();
  }, []);

  const handleExport = () => {
    if (caseData.score === 0) {
      setToast("No active case to export. Analyze a transcript first.");
      setTimeout(() => setToast(null), 3000);
      return;
    }
    const now = new Date();
    const ts = now.toISOString().replace(/[-:]/g, "").split(".")[0];
    const caseId = caseData.id ?? "UNKNOWN";
    const pkg = {
      case_id: caseId,
      transcript: caseData.transcript ?? "",
      risk_score: caseData.score,
      stage: caseData.stage,
      legal_findings: caseData.findings ?? [],
      interventions: caseData.interventions ?? [],
      exported_at: now.toISOString(),
    };
    const withIncident = (caseData.interventions ?? []).find(i => i.incident_id);
    if (withIncident) {
      pkg.intervention_result = {
        actions_taken: withIncident.actions_taken ?? [],
        incident_id: withIncident.incident_id,
        triggered_at: withIncident.timestamp ?? now.toISOString(),
      };
    }
    const blob = new Blob([JSON.stringify(pkg, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `bharat-kavach-case-${caseId}-${ts}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex bg-slate-950 min-h-screen">
      {/* Mini Sidebar */}
      <nav className="w-20 border-r border-slate-900 flex flex-col items-center py-8 gap-8">
        <div className="p-2 bg-accent-blue/20 rounded-xl">
          <Shield className="text-accent-blue" size={24} />
        </div>
        <div className="flex flex-col gap-6 text-slate-500">
          <Activity size={20} className="hover:text-white cursor-pointer transition-colors" title="Transcript Analysis"
            onClick={() => document.getElementById('transcript-panel')?.scrollIntoView({ behavior: 'smooth' })} />
          <MapIcon size={20} className="hover:text-white cursor-pointer transition-colors" title="Crime Map"
            onClick={() => document.getElementById('crime-map')?.scrollIntoView({ behavior: 'smooth' })} />
          <Users size={20} className="hover:text-white cursor-pointer transition-colors" title="Fraud Network"
            onClick={() => document.getElementById('fraud-network')?.scrollIntoView({ behavior: 'smooth' })} />
        </div>
        <div className="mt-auto">
          <Bell size={20} className="text-slate-500 hover:text-white cursor-pointer transition-colors" title="Interventions"
            onClick={() => document.getElementById('intervention-log')?.scrollIntoView({ behavior: 'smooth' })} />
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
            <button onClick={handleExport} className="bg-accent-blue hover:bg-blue-600 px-6 py-2 rounded-xl text-sm font-bold transition-all shadow-lg shadow-blue-500/20 flex items-center gap-2">
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
            <ForensicSignals signals={caseData.signals} />
            <div className="h-[400px]">
              <CaseHistory cases={caseData.history} onSelect={(c) => setCaseData(prev => ({...prev, score: c.risk_score, stage: c.stage, findings: c.legal_citations}))} />
            </div>
          </div>

          {/* Intelligence Visualizers */}
          <div className="col-span-12 lg:col-span-5 space-y-8">
            <div id="transcript-panel">
              <TranscriptPanel
                onResult={(data) => setCaseData(prev => ({
                  ...prev,
                  id: data.id ?? prev.id,
                  score: data.risk_score ?? prev.score,
                  stage: data.stage ?? prev.stage,
                  findings: data.legal_citations ?? prev.findings,
                  interventions: data.intervention_result
                    ? [...prev.interventions, {
                        type: 'FINANCIAL',
                        action: data.intervention_result.actions_taken?.[0] ?? 'TRIGGERED',
                        details: data.intervention_result.incident_id,
                        timestamp: new Date().toISOString(),
                        incident_id: data.intervention_result.incident_id,
                        actions_taken: data.intervention_result.actions_taken,
                      }]
                    : prev.interventions,
                  signals: {
                    behavioral: data.risk_score ?? prev.score,
                    legal: (data.legal_citations ?? []).some(f => f.verdict === 'confirmed_false') ? 0 : 100,
                    vision: prev.signals.vision,
                    protocol: prev.signals.protocol,
                  },
                }))}
                onSubmit={(text) => setCaseData(prev => ({ ...prev, transcript: text }))}
              />
            </div>
            <div id="crime-map" className="h-[350px]">
              <CrimeMap cases={caseData.history} />
            </div>
            <div id="fraud-network" className="h-[350px]">
              <FraudNetwork cases={caseData.history} />
            </div>
            <DocumentPanel />
            <CurrencyPanel />
          </div>

          {/* Legal & Intervention Logs */}
          <div className="col-span-12 lg:col-span-4 space-y-8">
            <LegalAudit findings={caseData.findings} />
            <div id="intervention-log">
              <InterventionLog logs={caseData.interventions} />
            </div>
          </div>
        </div>

        {/* Action Status Bar — only show after user has actively run an analysis */}
        {caseData.score > 70 && caseData.id !== null && (
          <div className="fixed bottom-8 right-8 left-28 translate-y-0">
            <div className="bg-red-500 p-4 rounded-2xl flex justify-between items-center shadow-2xl shadow-red-500/30">
              <div className="flex items-center gap-4 text-white">
                <AlertTriangle className="animate-bounce" />
                <div>
                  <p className="font-black text-sm uppercase">Automatic Intervention Triggered</p>
                  <p className="text-[10px] opacity-80 font-bold uppercase">
                    Actions: {(caseData.interventions.find(i => i.incident_id)?.actions_taken ?? []).join(' | ')} | Incident: {caseData.interventions.find(i => i.incident_id)?.incident_id ?? 'PENDING'} | Status: HOLD_QUEUED
                  </p>
                </div>
              </div>
              <button className="bg-white text-red-600 px-4 py-2 rounded-lg text-xs font-black hover:bg-slate-100 transition-colors">
                VIEW KILL-SWITCH LOGS
              </button>
            </div>
          </div>
        )}
        {toast && (
          <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 bg-slate-800 border border-slate-700 text-slate-200 text-sm font-medium px-6 py-3 rounded-xl shadow-xl">
            {toast}
          </div>
        )}
      </main>
    </div>
  );
};

export default Dashboard;
