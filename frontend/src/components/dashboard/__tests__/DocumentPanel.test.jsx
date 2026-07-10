// Feature: bharat-kavach-complete, Property 3
// Feature: bharat-kavach-complete, Property 4

import React from 'react';
import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import * as fc from 'fast-check';
import DocumentPanel from '../DocumentPanel';

// Mock framer-motion: all motion.* elements render as plain HTML elements
vi.mock('framer-motion', async () => {
  const { createElement } = await import('react');
  const makeTag = (tag) => {
    const Comp = ({
      children, className, style,
      initial, animate, exit, transition, whileHover, whileTap, layout,
      ...rest
    }) => createElement(tag, { className, style, ...rest }, children);
    Comp.displayName = `motion.${String(tag)}`;
    return Comp;
  };
  const motion = new Proxy({}, { get: (_, tag) => makeTag(String(tag)) });
  const AnimatePresence = ({ children }) => children ?? null;
  return { motion, AnimatePresence };
});

// Mock lucide-react icons to avoid SVG issues in jsdom
vi.mock('lucide-react', () => ({
  FileSearch: () => null,
  Upload: () => null,
  Loader2: () => null,
  AlertTriangle: () => null,
  ShieldAlert: () => null,
  ShieldCheck: () => null,
}));

/** Create a fake File for upload */
function makeFakeFile(name = 'test.pdf', type = 'application/pdf') {
  return new File(['hello'], name, { type });
}

/**
 * Render DocumentPanel, upload a file, submit, and wait for the result
 * container to appear. Returns after the component processes the fetch response.
 */
async function renderAndAnalyze(mockResponse) {
  // Use a controlled promise so we can verify state transitions
  let resolveJson;
  const jsonPromise = new Promise((res) => { resolveJson = res; });

  global.fetch = vi.fn().mockResolvedValueOnce({
    ok: true,
    json: () => jsonPromise,
  });

  render(<DocumentPanel />);

  const fileInput = document.querySelector('input[type="file"]');
  await userEvent.upload(fileInput, makeFakeFile());

  const analyzeBtn = screen.getByRole('button', { name: /analyze document/i });

  // Click and immediately resolve the JSON — this avoids timeout issues
  await act(async () => {
    await userEvent.click(analyzeBtn);
    resolveJson(mockResponse);
  });

  // Wait for loading to finish: button text returns to "ANALYZE DOCUMENT"
  await waitFor(
    () => {
      expect(screen.getByRole('button', { name: /analyze document/i })).not.toBeDisabled();
    },
    { timeout: 3000 }
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Property 3: Forgery alert threshold is correctly applied
// Validates: Requirements 3.5
// ─────────────────────────────────────────────────────────────────────────────
describe('Property 3: Forgery alert threshold is correctly applied', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it(
    'shows HIGH FORGERY CONFIDENCE iff verdict includes "Fake" AND confidence_score >= 0.75',
    async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.record({
            verdict: fc.string(),
            confidence_score: fc.float({ min: 0, max: 1, noNaN: true }),
          }),
          async ({ verdict, confidence_score }) => {
            document.body.innerHTML = '';
            vi.restoreAllMocks();

            await renderAndAnalyze({
              verdict,
              confidence_score,
              explanation: 'test explanation',
              forensic_signals: {},
            });

            const shouldShowAlert = verdict.includes('Fake') && confidence_score >= 0.75;

            // "High Forgery Confidence" text — CSS uppercases visually
            const alertEl = screen.queryByText(/high forgery confidence/i);

            if (shouldShowAlert) {
              expect(alertEl).not.toBeNull();
            } else {
              expect(alertEl).toBeNull();
            }

            // Red border on result container: class 'border-red-500'
            const redBorderedEls = document.querySelectorAll('.border-red-500');
            if (shouldShowAlert) {
              expect(redBorderedEls.length).toBeGreaterThan(0);
            } else {
              expect(redBorderedEls.length).toBe(0);
            }
          }
        ),
        { numRuns: 100 }
      );
    },
    30000 // 30s timeout for 100 property iterations
  );
});

// ─────────────────────────────────────────────────────────────────────────────
// Property 4: Document forensic signals render as proportional progress bars
// Validates: Requirements 3.4
// ─────────────────────────────────────────────────────────────────────────────
describe('Property 4: Document forensic signals render as proportional progress bars', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it(
    'each forensic signal key renders a bar with width equal to Math.round(value * 100) + "%"',
    async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.dictionary(
            fc.string({ minLength: 1, maxLength: 20 }),
            fc.float({ min: 0, max: 1, noNaN: true })
          ),
          async (forensic_signals) => {
            document.body.innerHTML = '';
            vi.restoreAllMocks();

            await renderAndAnalyze({
              verdict: 'Authentic',
              confidence_score: 0.5,
              explanation: 'test',
              forensic_signals,
            });

            // Each signal bar: inner div with inline style `width: X%`
            const allStyledEls = Array.from(document.querySelectorAll('[style]'));

            for (const [, value] of Object.entries(forensic_signals)) {
              const expectedWidth = `${Math.round(value * 100)}%`;
              const matchingBar = allStyledEls.find(
                (el) => el.style.width === expectedWidth
              );
              expect(
                matchingBar,
                `Expected a bar with width="${expectedWidth}" for value=${value}`
              ).not.toBeUndefined();
            }
          }
        ),
        { numRuns: 100 }
      );
    },
    30000 // 30s timeout for 100 property iterations
  );
});
