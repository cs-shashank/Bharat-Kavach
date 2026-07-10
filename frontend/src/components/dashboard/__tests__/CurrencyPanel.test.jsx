// Feature: bharat-kavach-complete, Property 5: Currency suspicion badge is correctly toggled

import React from 'react';
import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import * as fc from 'fast-check';
import CurrencyPanel from '../CurrencyPanel';

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
  Banknote: () => null,
  Upload: () => null,
  Loader2: () => null,
  AlertTriangle: () => null,
  CheckCircle: () => null,
  ShieldAlert: () => null,
  Shield: () => null,
}));

/** Create a fake JPEG File for upload */
function makeFakeJpeg(name = 'note.jpg') {
  return new File(['fake-image-content'], name, { type: 'image/jpeg' });
}

/**
 * Render CurrencyPanel, upload a file, click "VERIFY NOTE", and wait for the
 * result to appear. Returns after the component processes the fetch response.
 */
async function renderAndVerify(mockResponse) {
  // Controlled promise so we can resolve fetch JSON after the click
  let resolveJson;
  const jsonPromise = new Promise((res) => { resolveJson = res; });

  global.fetch = vi.fn().mockResolvedValueOnce({
    ok: true,
    json: () => jsonPromise,
  });

  render(<CurrencyPanel />);

  const fileInput = document.querySelector('input[type="file"]');
  await userEvent.upload(fileInput, makeFakeJpeg());

  const verifyBtn = screen.getByRole('button', { name: /verify note/i });

  // Click and immediately resolve the JSON — avoids timeout issues
  await act(async () => {
    await userEvent.click(verifyBtn);
    resolveJson(mockResponse);
  });

  // Wait for loading to finish: button re-enables with "VERIFY NOTE" text
  await waitFor(
    () => {
      expect(screen.getByRole('button', { name: /verify note/i })).not.toBeDisabled();
    },
    { timeout: 3000 }
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Property 5: Currency suspicion badge is correctly toggled
// Validates: Requirements 4.4, 4.5
// ─────────────────────────────────────────────────────────────────────────────
describe('Property 5: Currency suspicion badge is correctly toggled', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it(
    'shows red "Suspicious Note Detected" when is_suspicious=true and green "Note Appears Genuine" when is_suspicious=false, mutually exclusive',
    async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.boolean(),
          async (is_suspicious) => {
            document.body.innerHTML = '';
            vi.restoreAllMocks();

            await renderAndVerify({
              note_type: '500_INR',
              signals: {
                thread_detected: true,
                is_suspicious,
              },
            });

            const suspiciousBadge = screen.queryByText(/suspicious note detected/i);
            const genuineBadge = screen.queryByText(/note appears genuine/i);

            if (is_suspicious === true) {
              // Red badge must be present
              expect(suspiciousBadge).not.toBeNull();
              // Green badge must be absent (mutually exclusive)
              expect(genuineBadge).toBeNull();
            } else {
              // Green badge must be present
              expect(genuineBadge).not.toBeNull();
              // Red badge must be absent (mutually exclusive)
              expect(suspiciousBadge).toBeNull();
            }
          }
        ),
        { numRuns: 100 }
      );
    },
    30000 // 30s timeout for 100 property iterations
  );
});
