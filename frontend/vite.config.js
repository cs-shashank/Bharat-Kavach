import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    proxy: {
      '/analyze': 'http://localhost:8000',
      '/analyze-currency': 'http://localhost:8000',
      '/analyze-document': 'http://localhost:8000',
      '/cases': 'http://localhost:8000',
      '/metrics': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    }
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.js"],
  },
})
