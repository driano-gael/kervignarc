import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// En dev, le front (serveur Vite) et le backend (Uvicorn, port 8000) sont sur des origins
// distincts : on **proxifie** l'API, la sonde de santé et le WebSocket vers le backend.
// En production, FastAPI sert le build au même origin (E00US012) et ce proxy est inutile.
const CIBLE_BACKEND = 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': CIBLE_BACKEND,
      '/health': CIBLE_BACKEND,
      '/ws': { target: CIBLE_BACKEND, ws: true },
    },
  },
})
