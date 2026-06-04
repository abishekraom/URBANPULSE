import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import process from 'node:process'

const backendHttp = process.env.VITE_BACKEND_HTTP || 'http://localhost:8001'
const backendWs = process.env.VITE_BACKEND_WS || backendHttp.replace(/^http/, 'ws')

export default defineConfig({
  // Fast Refresh preamble has been flaky in this environment and can leave $RefreshSig$ undefined
  // in the browser even though the app compiles. Disable it for a stable dev dashboard.
  plugins: [react({ fastRefresh: false }), tailwindcss()],

  server: {
    proxy: {
      '/api': {
        target: backendHttp,
        changeOrigin: true,
      },
      '/ws': {
        target: backendWs,
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
