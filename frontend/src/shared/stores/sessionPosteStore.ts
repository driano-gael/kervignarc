// Session de poste (Zustand) — E04US001, ADR-0029.
//
// Détient le jeton de session de poste (délivré au **rattachement** par code) et la **cible** servie
// (tournoi, numéro), pour rouvrir directement dessus après une coupure. Persisté dans le
// `localStorage` : le CA veut une session qui **survit à la fermeture de l'onglet**, à une veille, à
// un redémarrage de la tablette — « le poste retrouve sa cible sans rien demander à personne ». Elle
// redevient invalide si le serveur redémarre ou si le tournoi est **terminé** (révocation) — l'app le
// détecte sur un 401 et purge la session (cf. `enregistrerSurNonAutorisePoste`).
//
// Le store porte aussi le **thème** du poste (D-26), appliqué au chargement et à chaque changement :
// c'est la préférence qui « revient toute seule » à la réouverture. Le jeton est joint via l'en-tête
// `X-Jeton-Poste` (inversion de dépendance : le client HTTP ne dépend pas de ce store).

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { enregistrerJetonPoste, enregistrerSurNonAutorisePoste } from '../api/client'
import { appliquerTheme, type Theme } from '../theme'

// La cible servie par le poste (miroir du DTO `PosteRattacheReponse`). Défini ici, dans `shared/`,
// pour que la feature `poste` en dépende (et non l'inverse) — même parti que `ScoreurConnecte`.
export interface CiblePoste {
  tournoi_id: number
  cible_index: number
}

interface SessionPosteState {
  jeton: string | null
  poste: CiblePoste | null
  theme: Theme | null
  definir: (session: { jeton: string; poste: CiblePoste }) => void
  effacer: () => void
  definirTheme: (theme: Theme | null) => void
}

export const useSessionPosteStore = create<SessionPosteState>()(
  persist(
    (set) => ({
      jeton: null,
      poste: null,
      theme: null,
      definir: ({ jeton, poste }) => set({ jeton, poste }),
      // La déconnexion (ou un 401) efface le rattachement, **pas** le thème : la tablette garde sa
      // préférence lumineuse pour le prochain rattachement (elle ne bouge pas de sa cible).
      effacer: () => set({ jeton: null, poste: null }),
      definirTheme: (theme) => {
        appliquerTheme(theme)
        set({ theme })
      },
    }),
    {
      name: 'kervignarc-session-poste',
      // À la réhydratation (ouverture de l'app), on ré-applique le thème persisté : il « revient
      // tout seul » sans que le bénévole ait à rebasculer (D-26, D-05 « l'onglet se ferme »).
      onRehydrateStorage: () => (etat) => appliquerTheme(etat?.theme ?? null),
    },
  ),
)

// Le client HTTP lit le jeton courant à chaque requête (en-tête `X-Jeton-Poste`).
enregistrerJetonPoste(() => useSessionPosteStore.getState().jeton)

// Un 401 alors qu'un jeton de poste était joint (tournoi terminé, serveur redémarré) purge le
// rattachement : l'UI repasse sur le formulaire de code (re-scan).
enregistrerSurNonAutorisePoste(() => useSessionPosteStore.getState().effacer())
