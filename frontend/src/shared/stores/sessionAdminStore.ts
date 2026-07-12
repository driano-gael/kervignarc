// Session administrateur (Zustand) — E10US002.
//
// Détient le jeton de session admin délivré par le backend à la connexion. Persisté dans le
// `localStorage` pour survivre à un rechargement de page (confort en salle) ; il redevient
// invalide si le serveur redémarre — l'app le détecte alors sur un 401 et le purge (cf.
// gestion d'erreur côté écran de création). Le jeton est joint automatiquement aux requêtes
// via `enregistrerJetonAdmin` (le client HTTP ne dépend pas de ce store).

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { enregistrerJetonAdmin } from '../api/client'

interface SessionAdminState {
  jeton: string | null
  definir: (jeton: string) => void
  effacer: () => void
}

export const useSessionAdminStore = create<SessionAdminState>()(
  persist(
    (set) => ({
      jeton: null,
      definir: (jeton) => set({ jeton }),
      effacer: () => set({ jeton: null }),
    }),
    { name: 'kervignarc-session-admin' },
  ),
)

// Le client HTTP lit le jeton courant à chaque requête (Authorization: Bearer <jeton>).
enregistrerJetonAdmin(() => useSessionAdminStore.getState().jeton)
