import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

function apiKeyFrom(filePath: string): string {
  try {
    const environment = readFileSync(filePath, 'utf8')
    const match = environment.match(/^\s*API_KEY\s*=\s*(.*)\s*$/m)
    const raw = match?.[1]?.trim() ?? ''
    if (raw.startsWith('"') && raw.endsWith('"')) {
      try { return JSON.parse(raw) as string } catch { return '' }
    }
    return raw.replace(/^'|'$/g, '').replace(/\s+#.*$/, '').trim()
  } catch {
    return ''
  }
}

function apiKeyForProxy(): string {
  return process.env.API_KEY?.trim()
    || apiKeyFrom(resolve(process.cwd(), '.env'))
    || apiKeyFrom(resolve(process.cwd(), '../backend/.env'))
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.API_URL || 'http://localhost:8000'

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          configure: (proxy) => {
            proxy.on('proxyReq', (proxyRequest) => {
              const apiKey = apiKeyForProxy()
              if (apiKey) proxyRequest.setHeader('X-API-Key', apiKey)
            })
          },
        },
      },
    },
  }
})
