// Feature: bharat-kavach-complete, Property 1: Non-empty transcript always triggers a POST

import React from 'react';
import { describe, it, expect, afterEach, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import * as fc from 'fast-check';
import TranscriptPanel from '../TranscriptPanel';

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
  FileText: () => null,
  Loader2: () => null,
  AlertTriangle: () => null,
  ScanSearch: () => null,
}));

// ─────────────────────────────────────────────────────────────────────────────
// Property 1: Non-empty transcript always triggers a POST
// Validates: Requirements 2.2, 8.2
// ─────────────────────────────────────────────────────────────────────────────
describe('Property 1: Non-empty transcript always triggers a POST', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it(
    'calls fetch exactly once with correct endpoint and body for any non-empty transcript',
    async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.string({ minLength: 1 }).filter((s) => s.trim().length > 0),
          async (transcript) => {
            document.body.innerHTML = '';
            vi.restoreAllMocks();

            // Mock fetch returning a successful response
            global.fetch = vi.fn().mockResolvedValueOnce({
              ok: true,
              json: () => Promise.resolve({ id: 1, status: 'SAVED' }),
            });

            const onResult = vi.fn();
            render(<TranscriptPanel onResult={onResult} />);

            const textarea = screen.getByRole('textbox');

            // Use fireEvent.change to set textarea value directly — avoids
            // userEvent.type interpreting special characters like `{` and `[`
            // as keyboard descriptors, while still triggering React's onChange.
            fireEvent.change(textarea, { target: { value: transcript } });

            // Verify textarea has the exact value set
            expect(textarea.value).toBe(transcript);

            const analyzeBtn = screen.getByRole('button', { name: /analyze/i });
            await userEvent.click(analyzeBtn);

            // Wait for fetch to be called
            await waitFor(() => {
              expect(global.fetch).toHaveBeenCalledTimes(1);
            });

            // Assert correct endpoint
            expect(global.fetch).toHaveBeenCalledWith(
              'http://localhost:8000/analyze',
              expect.objectContaining({
                method: 'POST',
                headers: expect.objectContaining({
                  'Content-Type': 'application/json',
                }),
                body: JSON.stringify({ transcript, user_id: 'OFFICER_001' }),
              })
            );
          }
        ),
        { numRuns: 100 }
      );
    },
    60000 // 60s timeout for 100 property iterations
  );
});

// ─────────────────────────────────────────────────────────────────────────────
// Example tests
// ─────────────────────────────────────────────────────────────────────────────
describe('TranscriptPanel example tests', () => {
  let onResult;

  beforeEach(() => {
    onResult = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('does not call fetch and shows error when transcript is empty', async () => {
    global.fetch = vi.fn();
    render(<TranscriptPanel onResult={onResult} />);

    const analyzeBtn = screen.getByRole('button', { name: /analyze/i });
    await userEvent.click(analyzeBtn);

    expect(global.fetch).not.toHaveBeenCalled();
    expect(screen.getByText('Transcript cannot be empty')).toBeInTheDocument();
  });

  it('does not call fetch and shows error when transcript is whitespace only', async () => {
    global.fetch = vi.fn();
    render(<TranscriptPanel onResult={onResult} />);

    const textarea = screen.getByRole('textbox');
    await userEvent.type(textarea, '   ');

    const analyzeBtn = screen.getByRole('button', { name: /analyze/i });
    await userEvent.click(analyzeBtn);

    expect(global.fetch).not.toHaveBeenCalled();
    expect(screen.getByText('Transcript cannot be empty')).toBeInTheDocument();
  });

  it('disables the ANALYZE button while fetch is in-flight', async () => {
    // Use a controlled promise so we can inspect loading state before resolution
    let resolveFetch;
    const fetchPromise = new Promise((res) => { resolveFetch = res; });

    global.fetch = vi.fn().mockReturnValueOnce(fetchPromise);

    render(<TranscriptPanel onResult={onResult} />);

    const textarea = screen.getByRole('textbox');
    await userEvent.type(textarea, 'Test transcript for loading state');

    const analyzeBtn = screen.getByRole('button', { name: /analyze/i });

    // Click without awaiting the fetch resolution
    await act(async () => {
      await userEvent.click(analyzeBtn);
    });

    // Button should be disabled while fetch is pending
    expect(analyzeBtn).toBeDisabled();

    // Now resolve the fetch
    await act(async () => {
      resolveFetch({ ok: true, json: () => Promise.resolve({ id: 1, status: 'SAVED' }) });
    });

    // Wait for button to become re-enabled
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /analyze/i })).not.toBeDisabled();
    });
  });

  it('shows error "Analysis failed. Please try again." when fetch rejects', async () => {
    global.fetch = vi.fn().mockRejectedValueOnce(new Error('Network error'));

    render(<TranscriptPanel onResult={onResult} />);

    const textarea = screen.getByRole('textbox');
    await userEvent.type(textarea, 'Test transcript');

    const analyzeBtn = screen.getByRole('button', { name: /analyze/i });

    await act(async () => {
      await userEvent.click(analyzeBtn);
    });

    await waitFor(() => {
      expect(screen.getByText('Analysis failed. Please try again.')).toBeInTheDocument();
    });

    // Button should be re-enabled after error
    expect(screen.getByRole('button', { name: /analyze/i })).not.toBeDisabled();
  });
});
