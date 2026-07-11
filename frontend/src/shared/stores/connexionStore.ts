// État UI de la connexion temps réel (Zustand) — E00US010.
//
// L'état **serveur** vit dans React Query ; l'état **UI** (ici, le statut du lien WebSocket
// affiché au scoreur, CDC technique §7) vit dans un store Zustand léger.

import { create } from 'zustand'

export type StatutConnexion = 'connexion' | 'connecte' | 'deconnecte'

interface ConnexionState {
  statut: StatutConnexion
  setStatut: (statut: StatutConnexion) => void
}

export const useConnexionStore = create<ConnexionState>((set) => ({
  statut: 'connexion',
  setStatut: (statut) => set({ statut }),
}))
