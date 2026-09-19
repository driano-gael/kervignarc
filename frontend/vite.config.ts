import react from '@vitejs/plugin-react'
import { configDefaults, defineConfig } from 'vitest/config'

// Extension `.js` exigée par `tsc` sur ce fichier (`moduleResolution: node16`) ; Vite la résout
// vers le source `.ts`.
import { CHEMINS_AVEC_DOM } from './src/test-environnement.js'

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
  // Tests (E14US002 — outillage de test de rendu, ADR-0053). `jsdom` fournit un DOM en mémoire aux
  // tests de composants (Testing Library) ; `test-setup.ts` étend `expect` (jest-dom) et nettoie le
  // DOM entre les tests.
  // ⚠️ Deux projets depuis E00US031 (ADR-0110) : instancier jsdom pour les 67 modules de logique
  // pure coûtait ~67 s sur 224 — mesuré, pas supposé. Les tests de logique tournent donc sous
  // `node`, **sans** `test-setup.ts`, dont `cleanup()` et `localStorage.clear()` y échoueraient.
  test: {
    projects: [
      {
        extends: true,
        test: {
          name: 'dom',
          environment: 'jsdom',
          setupFiles: ['./src/test-setup.ts'],
          include: ['src/**/*.test.tsx', ...CHEMINS_AVEC_DOM],
        },
      },
      {
        extends: true,
        test: {
          name: 'node',
          environment: 'node',
          include: ['src/**/*.test.ts'],
          exclude: [...configDefaults.exclude, ...CHEMINS_AVEC_DOM],
        },
      },
    ],
  },
})
