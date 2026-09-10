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
      // Use 127.0.0.1 explicitly so 'localhost -> ::1' (IPv6) can't redirect to a stray process.
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
