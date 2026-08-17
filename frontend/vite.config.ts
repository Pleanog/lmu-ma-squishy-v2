import fs from 'node:fs'
import path from 'node:path'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const certPath = env.VITE_DEV_HTTPS_CERT || ''
  const keyPath = env.VITE_DEV_HTTPS_KEY || ''
  const backendHttpTarget = env.VITE_BACKEND_HTTP_TARGET || 'http://127.0.0.1:8000'
  const backendWsTarget = env.VITE_BACKEND_WS_TARGET || backendHttpTarget.replace(/^http/, 'ws')

  const resolvedCertPath = certPath ? path.resolve(process.cwd(), certPath) : ''
  const resolvedKeyPath = keyPath ? path.resolve(process.cwd(), keyPath) : ''
  const hasHttpsFiles = !!resolvedCertPath && !!resolvedKeyPath && fs.existsSync(resolvedCertPath) && fs.existsSync(resolvedKeyPath)

  return {
    plugins: [vue()],
    server: {
      host: true,
      https: hasHttpsFiles
        ? {
            cert: fs.readFileSync(resolvedCertPath),
            key: fs.readFileSync(resolvedKeyPath),
          }
        : undefined,
      proxy: {
        '/api': {
          target: backendHttpTarget,
          changeOrigin: true,
          secure: false,
        },
        '/ws': {
          target: backendWsTarget,
          changeOrigin: true,
          secure: false,
          ws: true,
        },
      },
    },
  }
})