// Session de poste (Zustand) — E04US001, ADR-0029.
//
// Détient le jeton de session et la **cible** servie, persistés : le CA veut une session qui survit
// à la fermeture de l'onglet, à une veille, à un redémarrage — « le poste retrouve sa cible sans
// rien demander à personne ». Elle redevient invalide si le serveur redémarre ou si le tournoi est
// **terminé** (401 → purge). Le store porte aussi le **thème** du poste (D-26), la préférence qui
// revient toute seule. Jeton joint via `X-Jeton-Poste` (inversion de dépendance).

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { enregistrerJetonPoste, enregistrerSurNonAutorisePoste } from '../api/client'
import { appliquerTheme, type Theme } from '../theme'

// Ce que sert le poste (miroir du DTO `PosteRattacheReponse`). Défini ici, dans `shared/`, pour que
// la feature `poste` en dépende (et non l'inverse) — même parti que `ScoreurConnecte`.
//
// **Deux natures depuis E07US004** : une tablette de **cible** (qui saisit) et un **écran de salle**
// (qui informe). Le `type` est la clé du routage : le même code de rattachement, le même endpoint et
// le même jeton mènent à deux écrans différents. Le déduire de la présence de `cible_index` ferait
// dépendre une décision de navigation d'une valeur nulle — une inférence qui casse en silence le
// jour où un troisième type apparaît.
export type TypePoste = 'cible' | 'ecran'

export interface PosteRattache {
  tournoi_id: number
  type: TypePoste
  /** Renseigné pour un poste de **cible** uniquement. */
  cible_index: number | null
  /** Renseigné pour un **écran de salle** uniquement (« près du pas de tir »). */
  libelle: string | null
}

interface SessionPosteState {
  jeton: string | null
  poste: PosteRattache | null
  theme: Theme | null
  // « Ce navigateur est un poste de cible » — intention **persistante**, distincte de la présence
  // d'un jeton. Sans elle, une session révoquée (jeton perdu) renverrait la tablette vers l'écran
  // admin ; avec elle, on retombe sur le **formulaire de rattachement** (re-scan), conforme à D-13.
  estPoste: boolean
  // Rattachement réussi : pose le jeton + la cible **et** marque le navigateur comme poste.
  definir: (session: { jeton: string; poste: PosteRattache }) => void
  // Session perdue (révocation « tournoi terminé », redémarrage serveur) : efface jeton + cible mais
  // **reste un poste** (et garde le thème) → l'UI réaffiche le formulaire de rattachement.
  effacer: () => void
  // Détachement **explicite** (bouton « Détacher ») : quitte le mode poste → retour à l'app normale.
  detacher: () => void
  // Arrivée par le QR (`?poste=…`) : marque le navigateur comme poste avant même le rattachement.
  entrerModePoste: () => void
  definirTheme: (theme: Theme | null) => void
}

export const useSessionPosteStore = create<SessionPosteState>()(
  persist(
    (set) => ({
      jeton: null,
      poste: null,
      theme: null,
      estPoste: false,
      definir: ({ jeton, poste }) => set({ jeton, poste, estPoste: true }),
      effacer: () => set({ jeton: null, poste: null }),
      detacher: () => set({ jeton: null, poste: null, estPoste: false }),
      entrerModePoste: () => set({ estPoste: true }),
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
