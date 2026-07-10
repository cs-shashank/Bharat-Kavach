// Feature: bharat-kavach-complete, Property 10: CrimeMap pin color matches case-count thresholds

import { render, screen } from '@testing-library/react';
import fc from 'fast-check';
import CrimeMap, { pinColor } from '../CrimeMap';

// Mock framer-motion to avoid animation issues in jsdom
vi.mock('framer-motion', () => ({
  motion: new Proxy({}, {
    get: (_, tag) => {
      const { forwardRef, createElement } = require('react');
      return forwardRef(({ children, animate, transition, initial, ...props }, ref) =>
        createElement(tag, { ...props, ref }, children)
      );
    }
  }),
  AnimatePresence: ({ children }) => children,
}));

// Mock lucide-react to avoid SVG rendering issues in jsdom
vi.mock('lucide-react', () => ({
  Map: () => null,
}));

// **Validates: Requirements 7.4**
describe('CrimeMap', () => {
  describe('Property 10: pin color matches case-count thresholds', () => {
    it('returns correct color for all counts in [1, 20]', () => {
      fc.assert(
        fc.property(fc.integer({ min: 1, max: 20 }), (count) => {
          const color = pinColor(count);
          if (count >= 5) {
            expect(color).toBe('#ef4444');
          } else if (count >= 2) {
            expect(color).toBe('#f97316');
          } else {
            // count === 1
            expect(color).toBe('#eab308');
          }
        })
      );
    });
  });

  describe('Example test 1: empty cases shows "No incidents reported"', () => {
    it('renders "No incidents reported" when cases is empty and no fetchError', () => {
      render(<CrimeMap cases={[]} />);
      expect(screen.getByText('No incidents reported')).toBeInTheDocument();
    });
  });

  describe('Example test 2: fetchError shows "Data unavailable"', () => {
    it('renders "Data unavailable" when fetchError is true', () => {
      render(<CrimeMap cases={[]} fetchError={true} />);
      expect(screen.getByText('Data unavailable')).toBeInTheDocument();
    });
  });
});
