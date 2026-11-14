import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// O navegador não fala TCP: em desenvolvimento, as chamadas /api vão para o
// gateway HTTP do backend (backend/gateway_http.py, porta 8080), que repassa
// cada pesquisa ao agregador por socket TCP.
const GATEWAY = 'http://127.0.0.1:8080'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': GATEWAY },
  },
  preview: {
    proxy: { '/api': GATEWAY },
  },
})
