// Feature: bharat-kavach-complete, Property 11/13

import React from 'react';
import { describe, it, expect, afterEach, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import * as fc from 'fast-check';
import CitizenApp, { TRANSLATIONS } from '../CitizenApp';

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
  Send: () => null,
  Camera: () => null,
  User: () => null,
  Phone: () => null,
  MoreVertical: () => null,
  ShieldAlert: () => null,
  WifiOff: () => null,
  CheckCircle: () => null,
}));

const LANGUAGE_LABELS = { en: 'EN', hi: 'हिन्दी', ta: 'தமிழ்' };
const REQUIRED_KEYS = [
  'alertTitle', 'stagePrefix', 'reportBtn', 'helplineBtn',
  'safeMessage', 'offlineFallback', 'unknownStage',
];

// ─────────────────────────────────────────────────────────────────────────────
// Property 13: Translation map completeness (static assertion)
// Validates: Requirements 8.7
// ─────────────────────────────────────────────────────────────────────────────
describe('Property 13: Translation map completeness', () => {
  it('has all 7 required keys as non-empty strings for each of en, hi, ta', () => {
    for (const lang of ['en', 'hi', 'ta']) {
      expect(TRANSLATIONS[lang], `TRANSLATIONS["${lang}"] should exist`).toBeDefined();
      for (const key of REQUIRED_KEYS) {
        const value = TRANSLATIONS[lang][key];
        expect(
          typeof value === 'string' && value.length > 0,
          `TRANSLATIONS["${lang}"]["${key}"] should be a non-empty string, got: ${JSON.stringify(value)}`
        ).toBe(true);
      }
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Property 11: CitizenApp alert language is always consistent with selected language
// Validates: Requirements 8.3, 8.5, 8.7
// ─────────────────────────────────────────────────────────────────────────────
describe('Property 11: CitizenApp alert language is always consistent with selected language', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it(
    'alert title, report and helpline button text match the selected language translations',
    async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.constantFrom('en', 'hi', 'ta'),
          fc.float({ min: 60, max: 100, noNaN: true }),
          async (language, score) => {
            document.body.innerHTML = '';
            vi.restoreAllMocks();

            // Mock fetch to return a high-risk response
            global.fetch = vi.fn().mockResolvedValueOnce({
              ok: true,
              json: () => Promise.resolve({ risk_score: score, stage: 'Digital Arrest' }),
            });

            render(<CitizenApp />);

            // Select the target language by clicking the language button
            const langLabel = LANGUAGE_LABELS[language];
            const langBtn = screen.getByRole('button', { name: langLabel });
            await userEvent.click(langBtn);

            // Type a message and press Enter
            const input = document.querySelector('input[type="text"]');
            await userEvent.type(input, 'test message');
            await userEvent.keyboard('{Enter}');

            // Wait for the Send button to re-enable (fetch resolved, loading done)
            await waitFor(
              () => {
                const sendBtn = document.querySelector('button[class*="bg-\\[#00a884\\]"]');
                if (sendBtn) {
                  expect(sendBtn).not.toBeDisabled();
                }
              },
              { timeout: 5000 }
            );

            // Wait for the alert banner to appear (score >= 60 → red alert)
            await waitFor(
              () => {
                const alertTitle = screen.queryByText(TRANSLATIONS[language].alertTitle);
                expect(alertTitle, `Expected alert title for language "${language}"`).not.toBeNull();
              },
              { timeout: 5000 }
            );

            // Assert alert title text matches selected language
            expect(screen.getByText(TRANSLATIONS[language].alertTitle)).toBeTruthy();

            // Assert REPORT button text matches selected language
            expect(screen.getByText(TRANSLATIONS[language].reportBtn)).toBeTruthy();

            // Assert CALL helpline button text matches selected language
            expect(screen.getByText(TRANSLATIONS[language].helplineBtn)).toBeTruthy();
          }
        ),
        { numRuns: 20 }
      );
    },
    60000
  );

  // Example: score < 60 → safe message shown, no red alert banner
  it('shows safe message when score < 60', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ risk_score: 30, stage: 'Digital Arrest' }),
    });

    render(<CitizenApp />);

    const input = document.querySelector('input[type="text"]');
    await userEvent.type(input, 'hello');
    await userEvent.keyboard('{Enter}');

    // Wait for loading to finish
    await waitFor(
      () => {
        expect(screen.queryByText(TRANSLATIONS['en'].safeMessage)).not.toBeNull();
      },
      { timeout: 5000 }
    );

    expect(screen.getByText(TRANSLATIONS['en'].safeMessage)).toBeTruthy();
    // No red alert banner
    expect(screen.queryByText(TRANSLATIONS['en'].alertTitle)).toBeNull();
  });

  // Example: fetch rejects → offline fallback text shown
  it('shows offline fallback when fetch rejects', async () => {
    global.fetch = vi.fn().mockRejectedValueOnce(new Error('Network error'));

    render(<CitizenApp />);

    const input = document.querySelector('input[type="text"]');
    await userEvent.type(input, 'hello');
    await userEvent.keyboard('{Enter}');

    await waitFor(
      () => {
        expect(screen.queryByText(TRANSLATIONS['en'].offlineFallback)).not.toBeNull();
      },
      { timeout: 5000 }
    );

    expect(screen.getByText(TRANSLATIONS['en'].offlineFallback)).toBeTruthy();
    expect(screen.queryByText(TRANSLATIONS['en'].alertTitle)).toBeNull();
  });
});
