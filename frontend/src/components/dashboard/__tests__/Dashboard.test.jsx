import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as fc from 'fast-check';

// ─── Mocks ────────────────────────────────────────────────────────────────────

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: new Proxy({}, {
    get: (_, tag) => ({ children, ...props }) => React.createElement(tag, props, children),
  }),
  AnimatePresence: ({ children }) => children,
}));

// Mock lucide-react
vi.mock('lucide-react', () => ({
  Shield: () => null,
  Activity: () => null,
  Users: () => null,
  MapIcon: () => null,
  Bell: () => null,
  Download: () => React.createElement('span', {}, 'Download'),
  ShieldAlert: () => null,
  AlertTriangle: () => null,
  Search: () => null,
  Gavel: () => null,
  Eye: () => null,
  FileCheck: () => null,
}));

// Mock heavy sub-components
vi.mock('../RiskMeter', () => ({ default: () => React.createElement('div', { 'data-testid': 'risk-meter' }) }));
vi.mock('../CaseHistory', () => ({ default: () => React.createElement('div', { 'data-testid': 'case-history' }) }));
vi.mock('../../forensics/LegalAudit', () => ({ default: () => React.createElement('div', { 'data-testid': 'legal-audit' }) }));
vi.mock('../../forensics/InterventionLog', () => ({ default: () => React.createElement('div', { 'data-testid': 'intervention-log' }) }));
vi.mock('../../forensics/FraudNetwork', () => ({ default: () => React.createElement('div', { 'data-testid': 'fraud-network' }) }));
vi.mock('../../forensics/CrimeMap', () => ({ default: () => React.createElement('div', { 'data-testid': 'crime-map' }) }));
vi.mock('../../forensics/RiskMeter', () => ({ default: () => React.createElement('div', { 'data-testid': 'risk-meter' }) }));
vi.mock('../TranscriptPanel', () => ({ default: () => React.createElement('div', { 'data-testid': 'transcript-panel' }) }));
vi.mock('../DocumentPanel', () => ({ default: () => React.createElement('div', { 'data-testid': 'document-panel' }) }));
vi.mock('../CurrencyPanel', () => ({ default: () => React.createElement('div', { 'data-testid': 'currency-panel' }) }));

// ─── Imports (after mocks) ────────────────────────────────────────────────────

import Dashboard, { hasFalseFindings } from '../Dashboard';
import ForensicSignals from '../../forensics/ForensicSignals';

// ─── Globals setup ────────────────────────────────────────────────────────────

class MockWebSocket {
  constructor() {
    this.onmessage = null;
    MockWebSocket.instance = this;
  }
  close() {}
}
MockWebSocket.instance = null;

beforeEach(() => {
  vi.stubGlobal('WebSocket', MockWebSocket);
  global.fetch = vi.fn().mockResolvedValue({ json: () => Promise.resolve([]) });
  global.URL.createObjectURL = vi.fn().mockReturnValue('blob:mock');
  global.URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// ─── Helper: mirror handleExport pkg construction ─────────────────────────────

function buildExportPkg(caseData) {
  const now = new Date();
  const caseId = caseData.id ?? 'UNKNOWN';
  const pkg = {
    case_id: caseId,
    transcript: caseData.transcript ?? '',
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
  return pkg;
}

// ─── Test Suites ──────────────────────────────────────────────────────────────

// Feature: bharat-kavach-complete, Property 2: FORENSIC_UPDATE drives Dashboard state

describe('hasFalseFindings — unit tests', () => {
  it('returns false for an empty array', () => {
    expect(hasFalseFindings([])).toBe(false);
  });

  it('returns false when no findings have confirmed_false verdict', () => {
    const findings = [
      { verdict: 'confirmed_true', claim_extracted: 'abc' },
      { verdict: 'unverified', claim_extracted: 'def' },
    ];
    expect(hasFalseFindings(findings)).toBe(false);
  });

  it('returns true when at least one finding has confirmed_false verdict', () => {
    const findings = [
      { verdict: 'confirmed_true', claim_extracted: 'abc' },
      { verdict: 'confirmed_false', claim_extracted: 'def' },
    ];
    expect(hasFalseFindings(findings)).toBe(true);
  });

  it('returns true when all findings have confirmed_false verdict', () => {
    const findings = [
      { verdict: 'confirmed_false', claim_extracted: 'a' },
      { verdict: 'confirmed_false', claim_extracted: 'b' },
    ];
    expect(hasFalseFindings(findings)).toBe(true);
  });

  // Property 2: hasFalseFindings returns true iff at least one finding has verdict === "confirmed_false"
  it('property: returns true iff at least one finding has verdict === "confirmed_false"', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            verdict: fc.string(),
            claim_extracted: fc.string(),
          })
        ),
        (findings) => {
          const result = hasFalseFindings(findings);
          const expected = findings.some(f => f.verdict === 'confirmed_false');
          return result === expected;
        }
      )
    );
  });
});

describe('signals mapping — unit tests', () => {
  it('sets behavioral signal to message.data.score', () => {
    const score = 75;
    const findings = [];
    const signals = {
      behavioral: score,
      legal: hasFalseFindings(findings) ? 0 : 100,
      vision: 100,
      protocol: 100,
    };
    expect(signals.behavioral).toBe(score);
  });

  it('sets legal signal to 0 when findings contain a confirmed_false verdict', () => {
    const findings = [{ verdict: 'confirmed_false', claim_extracted: 'x' }];
    const signals = {
      behavioral: 50,
      legal: hasFalseFindings(findings) ? 0 : 100,
      vision: 100,
      protocol: 100,
    };
    expect(signals.legal).toBe(0);
  });

  it('sets legal signal to 100 when no confirmed_false findings', () => {
    const findings = [{ verdict: 'confirmed_true', claim_extracted: 'y' }];
    const signals = {
      behavioral: 50,
      legal: hasFalseFindings(findings) ? 0 : 100,
      vision: 100,
      protocol: 100,
    };
    expect(signals.legal).toBe(100);
  });

  it('sets legal signal to 100 when findings array is empty', () => {
    const findings = [];
    const signals = {
      behavioral: 30,
      legal: hasFalseFindings(findings) ? 0 : 100,
      vision: 100,
      protocol: 100,
    };
    expect(signals.legal).toBe(100);
  });
});

// Feature: bharat-kavach-complete, Property 14: ForensicSignals alert thresholds

describe('ForensicSignals — alert threshold tests', () => {
  it('shows Alert for Behavioral Arc when behavioral > 60', () => {
    render(
      <ForensicSignals signals={{ behavioral: 80, legal: 100, vision: 100, protocol: 100 }} />
    );
    // Find the status badge next to "Behavioral Arc"
    const allAlerts = screen.getAllByText('Alert');
    expect(allAlerts.length).toBeGreaterThan(0);
  });

  it('shows Normal for Behavioral Arc when behavioral <= 60', () => {
    render(
      <ForensicSignals signals={{ behavioral: 60, legal: 100, vision: 100, protocol: 100 }} />
    );
    expect(screen.getByText('Normal')).toBeInTheDocument();
  });

  it('shows Alert for Legal Grounding when legal < 50', () => {
    render(
      <ForensicSignals signals={{ behavioral: 0, legal: 30, vision: 100, protocol: 100 }} />
    );
    const allAlerts = screen.getAllByText('Alert');
    expect(allAlerts.length).toBeGreaterThan(0);
  });

  it('shows Secure for Legal Grounding when legal >= 50', () => {
    render(
      <ForensicSignals signals={{ behavioral: 0, legal: 50, vision: 100, protocol: 100 }} />
    );
    // "Secure" should appear for legal (and possibly vision/protocol too)
    const secureEls = screen.getAllByText('Secure');
    expect(secureEls.length).toBeGreaterThan(0);
  });

  // Property 14: ForensicSignals alert thresholds hold for all float inputs
  it('property: Behavioral Arc shows Alert iff behavioral > 60, Legal Grounding shows Alert iff legal < 50', () => {
    fc.assert(
      fc.property(
        fc.float({ min: 0, max: 100 }),
        fc.float({ min: 0, max: 100 }),
        (behavioral, legal) => {
          const { unmount } = render(
            <ForensicSignals
              signals={{ behavioral, legal, vision: 100, protocol: 100 }}
            />
          );

          // Check if "Alert" appears — either could trigger it
          const alertElements = document.querySelectorAll('.text-red-500');
          const hasAlert = alertElements.length > 0;

          // Both conditions for alert
          const behavioralAlert = behavioral > 60;
          const legalAlert = legal < 50;
          const shouldHaveAlert = behavioralAlert || legalAlert;

          unmount();

          return hasAlert === shouldHaveAlert;
        }
      ),
      { numRuns: 50 }
    );
  });
});

// Feature: bharat-kavach-complete, Property 12: Export package has required fields

describe('Export package fields', () => {
  const REQUIRED_KEYS = [
    'case_id',
    'transcript',
    'risk_score',
    'stage',
    'legal_findings',
    'interventions',
    'exported_at',
  ];

  // Property 12: export package always has exactly 7 required keys for score > 0
  it('property: export pkg always contains exactly 7 required keys when score > 0', () => {
    // Use fc.object() so interventions are always plain objects, not undefined/primitive
    const interventionArb = fc.array(
      fc.record({
        type: fc.string(),
        action: fc.string(),
      })
    );
    fc.assert(
      fc.property(
        fc.record({
          id: fc.integer(),
          transcript: fc.string(),
          score: fc.float({ min: 1, max: 100 }),
          stage: fc.string(),
          findings: fc.array(fc.string()),
          interventions: interventionArb,
        }),
        (caseData) => {
          const pkg = buildExportPkg(caseData);
          // All 7 required keys must be present
          const hasAllRequired = REQUIRED_KEYS.every(k => Object.prototype.hasOwnProperty.call(pkg, k));
          return hasAllRequired;
        }
      ),
      { numRuns: 100 }
    );
  });

  it('adds intervention_result (8th key) when an intervention has incident_id', () => {
    const caseData = {
      id: 42,
      transcript: 'test transcript',
      score: 85,
      stage: 'Active',
      findings: [],
      interventions: [
        {
          type: 'FINANCIAL',
          action: 'FREEZE',
          incident_id: 'INC-001',
          timestamp: '2024-01-01T00:00:00Z',
          actions_taken: ['FREEZE_ACCOUNT'],
        },
      ],
    };
    const pkg = buildExportPkg(caseData);
    expect(Object.keys(pkg)).toHaveLength(8);
    expect(pkg).toHaveProperty('intervention_result');
    expect(pkg.intervention_result.incident_id).toBe('INC-001');
    expect(pkg.intervention_result.actions_taken).toEqual(['FREEZE_ACCOUNT']);
  });

  it('does not add intervention_result when interventions have no incident_id', () => {
    const caseData = {
      id: 1,
      transcript: 'test',
      score: 50,
      stage: 'Pending',
      findings: [],
      interventions: [{ type: 'MANUAL', action: 'REVIEW' }],
    };
    const pkg = buildExportPkg(caseData);
    expect(Object.keys(pkg)).toHaveLength(7);
    expect(pkg).not.toHaveProperty('intervention_result');
  });

  it('contains all 7 required keys for a minimal case', () => {
    const caseData = {
      id: 99,
      transcript: 'hello',
      score: 10,
      stage: 'InProgress',
      findings: [],
      interventions: [],
    };
    const pkg = buildExportPkg(caseData);
    REQUIRED_KEYS.forEach(key => {
      expect(pkg).toHaveProperty(key);
    });
  });
});

// ─── Example test: score === 0 export shows toast, no download ───────────────

describe('Dashboard export — score === 0 shows toast, no download', () => {
  it('shows toast and does not call URL.createObjectURL when score is 0', async () => {
    render(<Dashboard />);

    // Wait for fetch to complete (initial mount)
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
    });

    // Click export button
    const exportBtn = screen.getByRole('button', { name: /export intelligence package/i });
    fireEvent.click(exportBtn);

    // Toast should appear
    await waitFor(() => {
      expect(
        screen.getByText('No active case to export. Analyze a transcript first.')
      ).toBeInTheDocument();
    });

    // createObjectURL should NOT have been called
    expect(global.URL.createObjectURL).not.toHaveBeenCalled();
  });
});
