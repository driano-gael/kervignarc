// Fournisseurs racine de l'app (E00US010) : cache état-serveur (React Query) + branchement
// du client temps réel (WebSocket). Le câblage de l'app est centralisé ici.

import { QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useRealtime } from '../shared/realtime/useRealtime'
import { queryClient } from './queryClient'

// Composant sans rendu : ouvre la connexion temps réel dans le contexte React Query.
function ConnexionTempsReel() {
  useRealtime()
  return null
}

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ConnexionTempsReel />
      {children}
    </QueryClientProvider>
  )
}
