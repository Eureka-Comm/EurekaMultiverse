import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import fs from 'node:fs'
import path from 'node:path'

// Load DEEPSEEK_API_KEY from the repo-root .env so the Copilot proxy works without
// requiring the env var to be set on the shell that launches Vite.
function loadRootEnvKey(): string | undefined {
  try {
    const rootEnv = path.resolve(process.cwd(), '..', '.env')
    const text = fs.readFileSync(rootEnv, 'utf8')
    const m = text.match(/^\s*DEEPSEEK_API_KEY\s*=\s*"?([^"\r\n]+)"?\s*$/m)
    return m ? m[1] : undefined
  } catch {
    return undefined
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api/copilot': {
        target: 'https://api.deepseek.com',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api\/copilot/, '/chat/completions'),
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            const apiKey = process.env.DEEPSEEK_API_KEY || loadRootEnvKey()
            if (apiKey) {
              proxyReq.setHeader('Authorization', `Bearer ${apiKey}`)
            }
          })
        }
      }
    }
  }
})
