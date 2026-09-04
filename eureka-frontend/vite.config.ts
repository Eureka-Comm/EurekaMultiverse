import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
// NOTE (auth): the LLM copilot is NOT proxied here and NO DEEPSEEK_API_KEY is loaded on the
// frontend. The browser calls the EUREKA backend at VITE_EUREKA_API_URL (or http://localhost:8000
// in dev). Only the backend holds the DeepSeek key. This keeps credentials out of the browser
// bundle for the public deployment.
export default defineConfig({
  plugins: [react(), tailwindcss()],
})
