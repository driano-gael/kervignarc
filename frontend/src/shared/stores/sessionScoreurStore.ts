// Session scoreur (Zustand) — E10US003.
//
// Détient le jeton de session scoreur (délivré par le backend à la connexion **par code**) et
// l'identité du scoreur (nom, tournoi) pour l'afficher après un rechargement. Persisté dans le
// `localStorage` : le CA veut une session qui **survit à la fermeture de l'onglet** le temps d'une
// journée de tournoi. Elle redevient invalide si le serveur redémarre ou si l'admin **supprime** le
// scoreur — l'app le détecte alors sur un 401 et purge la session (cf. `enregistrerSurNonAutorise-
// Scoreur`). Le jeton est joint automatiquement via l'en-tête `X-Jeton-Scoreur` (le client HTTP ne
// dépend pas de ce store : inversion de dépendance, comme la session admin).

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { enregistrerJetonScoreur, enregistrerSurNonAutoriseScoreur } from '../api/client'

// Identité renvoyée à la connexion : de quoi saluer le scoreur par son nom et savoir de quel tournoi
// il valide (il n'est rattaché à **aucune cible** — scoreur itinérant, D-12). Défini ici, dans
// `shared/`, pour que la feature `scoreur-session` en dépende (et non l'inverse).
export interface ScoreurConnecte {
  id: number
  tournoi_id: number
  nom: string
}

interface SessionScoreurState {
  jeton: string | null
  scoreur: ScoreurConnecte | null
  definir: (session: { jeton: string; scoreur: ScoreurConnecte }) => void
  effacer: () => void
}

export const useSessionScoreurStore = create<SessionScoreurState>()(
  persist(
    (set) => ({
      jeton: null,
      scoreur: null,
      definir: ({ jeton, scoreur }) => set({ jeton, scoreur }),
      effacer: () => set({ jeton: null, scoreur: null }),
    }),
    { name: 'kervignarc-session-scoreur' },
  ),
)

// Le client HTTP lit le jeton courant à chaque requête (en-tête `X-Jeton-Scoreur`).
enregistrerJetonScoreur(() => useSessionScoreurStore.getState().jeton)

// Un 401 alors qu'un jeton scoreur était joint (session invalide, ex. scoreur supprimé) purge la
// session : l'UI repasse automatiquement sur le formulaire de code.
enregistrerSurNonAutoriseScoreur(() => useSessionScoreurStore.getState().effacer())
