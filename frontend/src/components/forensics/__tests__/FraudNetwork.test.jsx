// Feature: bharat-kavach-complete, Property 8/9

import { describe, it, expect } from 'vitest';
import * as fc from 'fast-check';
import { deriveNetwork } from '../FraudNetwork.jsx';

// ─── Arbitraries ─────────────────────────────────────────────────────────────

const caseArb = fc.record({
  id: fc.integer({ min: 1 }),
  risk_score: fc.float({ min: 0, max: 100, noNaN: true }),
  timestamp: fc.date(),
  transcript: fc.constant(''),
});

const caseArrayArb = fc.array(caseArb, { minLength: 1 });

const phoneArb = fc.stringMatching(/^[6-9]\d{9}$/);
const phoneArrayArb = fc.array(phoneArb, { minLength: 1, maxLength: 5 });

// ─── Property 8: FraudNetwork primary suspect selection is deterministic ──────
// Validates: Requirements 6.2, 6.4

describe('Property 8: FraudNetwork primary suspect selection is deterministic', () => {
  it('returns null when no case has risk_score > 70', () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            id: fc.integer({ min: 1 }),
            risk_score: fc.float({ min: 0, max: 70, noNaN: true }),
            timestamp: fc.date(),
            transcript: fc.constant(''),
          }),
          { minLength: 1 },
        ),
        (cases) => {
          // Ensure ALL cases have risk_score <= 70 (none strictly > 70)
          const allLow = cases.map(c => ({ ...c, risk_score: Math.min(c.risk_score, 70) }));
          const result = deriveNetwork(allLow);
          expect(result).toBeNull();
        },
      ),
    );
  });

  it('selects the high-risk case with the latest timestamp as primary', () => {
    fc.assert(
      fc.property(caseArrayArb, (cases) => {
        const highRisk = cases.filter(c => c.risk_score > 70);
        if (highRisk.length === 0) {
          // No high-risk cases → result must be null
          expect(deriveNetwork(cases)).toBeNull();
          return;
        }

        const result = deriveNetwork(cases);
        expect(result).not.toBeNull();

        // Find expected primary: max timestamp, tiebreak by largest id
        const expected = highRisk.reduce((best, c) => {
          const tBest = new Date(best.timestamp).getTime();
          const tC = new Date(c.timestamp).getTime();
          if (tC > tBest) return c;
          if (tC === tBest) return c.id > best.id ? c : best;
          return best;
        });

        expect(result.primary.id).toBe(expected.id);
      }),
    );
  });

  it('on timestamp tie, the case with the largest id wins', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1 }),
        fc.integer({ min: 1 }),
        (idA, idB) => {
          fc.pre(idA !== idB);
          const sharedTimestamp = new Date('2024-01-01T00:00:00.000Z');
          const caseA = { id: idA, risk_score: 80, timestamp: sharedTimestamp, transcript: '' };
          const caseB = { id: idB, risk_score: 80, timestamp: sharedTimestamp, transcript: '' };
          const cases = [caseA, caseB];

          const result = deriveNetwork(cases);
          expect(result).not.toBeNull();

          const expectedId = Math.max(idA, idB);
          expect(result.primary.id).toBe(expectedId);
        },
      ),
    );
  });
});

// ─── Property 9: Phone number extraction is regex-complete ────────────────────
// Validates: Requirements 6.1, 6.3

describe('Property 9: Phone number extraction is regex-complete', () => {
  it('all generated phone numbers appear in returned phones array', () => {
    fc.assert(
      fc.property(phoneArrayArb, (phones) => {
        const transcript = phones.map(p => 'Call me at ' + p).join(' ');
        const caseObj = {
          id: 1,
          risk_score: 100,
          timestamp: new Date(),
          transcript,
        };

        const result = deriveNetwork([caseObj]);
        expect(result).not.toBeNull();

        for (const phone of phones) {
          expect(result.phones).toContain(phone);
        }
      }),
    );
  });

  it('produces an empty phones array when transcript has no valid phone pattern', () => {
    const caseObj = {
      id: 1,
      risk_score: 100,
      timestamp: new Date(),
      transcript: 'Hello world',
    };

    const result = deriveNetwork([caseObj]);
    expect(result).not.toBeNull();
    expect(result.phones).toHaveLength(0);
  });
});
