import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
// (auth) NO DEEPSEEK_API_KEY is loaded here. In production the browser reaches the API via the
// same-origin path /api (nginx proxies it to the backend). In local dev Vite proxies /api to the
// backend so the dev server also uses the same relative /api base — the backend (and only the
// backend) holds the DeepSeek key. Keep credentials out of the browser bundle.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // Local dev: forward every /api call (work, evidence, copilot) to the backend.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
