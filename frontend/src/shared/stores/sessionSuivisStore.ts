// Session « suivis » (Zustand) — E07US006.
//
// Mémorise localement la liste des archers que l'utilisateur a choisi de **suivre** : la vue publique
// s'ouvre alors directement sur eux, sans avoir à les rechercher à chaque fois (D-09, CDC UX §6.3).
// Même principe que le jeton de poste (`localStorage`, survit à la fermeture de l'onglet le temps de
// la journée) mais **sans aucun compte ni jeton serveur** : la lecture publique est anonyme, il n'y a
// rien à authentifier. Le store ne s'enregistre donc **pas** auprès du client HTTP — contrairement
// aux sessions poste/scoreur, il n'a pas d'en-tête à joindre ni de 401 à écouter.
//
// « Liste de suivis » (arbitrage métier du 20/07) : pas de notion privilégiée de « moi » — un archer
// suivi en vaut un autre (un accompagnateur/coach en suit plusieurs). Le CA v0.1 « c'est moi » / « ce
// n'est pas moi » devient donc suivre / ne plus suivre, par archer.

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// Un archer suivi, réduit à ce qu'il faut pour le retrouver : son id et le tournoi dont il relève. On
// porte le `tournoiId` parce qu'on peut suivre des archers de tournois **différents** (intérieur et
// extérieur en parallèle sont une capacité voulue) ; la vue ne montre que ceux du tournoi affiché. Le
// **nom n'est pas mémorisé** : il est résolu à la volée depuis la liste des archers (vérité serveur),
// pour qu'un archer renommé garde son suivi sans afficher un nom périmé.
export interface ArcherSuivi {
  archerId: number
  tournoiId: number
}

interface SessionSuivisState {
  suivis: ArcherSuivi[]
  suivre: (archer: ArcherSuivi) => void
  nePlusSuivre: (archerId: number) => void
}

export const useSessionSuivisStore = create<SessionSuivisState>()(
  persist(
    (set) => ({
      suivis: [],
      suivre: (archer) =>
        set((etat) =>
          // Idempotent : re-suivre un archer déjà dans la liste ne le duplique pas.
          etat.suivis.some((s) => s.archerId === archer.archerId)
            ? etat
            : { suivis: [...etat.suivis, archer] },
        ),
      nePlusSuivre: (archerId) =>
        set((etat) => ({ suivis: etat.suivis.filter((s) => s.archerId !== archerId) })),
    }),
    { name: 'kervignarc-session-suivis' },
  ),
)
