// API base URL — uses VITE_API_URL env var in production (Railway),
// falls back to localhost for local development.
export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
