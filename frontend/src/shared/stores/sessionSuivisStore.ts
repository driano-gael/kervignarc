// Session « suivis » (Zustand) — E07US006.
//
// Mémorise localement les archers que l'utilisateur a choisi de **suivre** (D-09, CDC UX §6.3).
// Même principe que le jeton de poste (`localStorage`) mais **sans aucun compte ni jeton serveur**
// : la lecture publique est anonyme. Le store ne s'enregistre donc **pas** auprès du client HTTP —
// il n'a ni en-tête à joindre ni 401 à écouter. « Liste de suivis » (arbitrage du 20/07) : pas de
// notion privilégiée de « moi », un accompagnateur en suit plusieurs — le CA « c'est moi » devient
// donc suivre / ne plus suivre, par archer.

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
  /** La bascule « mes archers / tout » de l'appli publique (E16US004).
   *
   * **Une préférence de lecture, donc globale** — pas par tournoi, contrairement aux suivis ;
   * `focus.modeEffectif` la retombe sur « tout » sur un tournoi où l'on ne suit personne.
   * ⚠️ **Armée par défaut** (`true`), arbitrage du 08/08/2026 : le CA d'E07US005 promet « Mon
   * chemin » par défaut **dès qu'on suit quelqu'un**, et l'interrupteur unique d'E16US004 ayant
   * dissous les défauts par vue, la laisser à `false` révoquait ce CA en silence.
   */
  centrerSurSuivis: boolean
  suivre: (archer: ArcherSuivi) => void
  nePlusSuivre: (archerId: number) => void
  centrer: (valeur: boolean) => void
}

export const useSessionSuivisStore = create<SessionSuivisState>()(
  persist(
    (set) => ({
      suivis: [],
      centrerSurSuivis: true,
      suivre: (archer) =>
        set((etat) =>
          // Idempotent : re-suivre un archer déjà dans la liste ne le duplique pas.
          etat.suivis.some((s) => s.archerId === archer.archerId)
            ? etat
            : { suivis: [...etat.suivis, archer] },
        ),
      nePlusSuivre: (archerId) =>
        set((etat) => ({ suivis: etat.suivis.filter((s) => s.archerId !== archerId) })),
      centrer: (valeur) => set({ centrerSurSuivis: valeur }),
    }),
    {
      name: 'kervignarc-session-suivis',
      // ⚠️ **`version: 1` + `migrate` sont indispensables ici**, et pas de la précaution générale.
      // `persist` fusionne **superficiellement** : une clé **absente** retombe sur la valeur
      // initiale, mais un premier jet de cette US a déjà écrit `centrerSurSuivis: false` chez tout
      // appareil ayant ouvert la branche — et là, la valeur **persistée gagne**. L'arbitrage aurait
      // été invisible précisément sur les machines qui comptent. La migration ne touche **que** la
      // préférence d'affichage, jamais la liste des suivis.
      version: 1,
      migrate: (etatPersiste, versionLue) => {
        const etat = (etatPersiste ?? {}) as Partial<SessionSuivisState>
        if (versionLue >= 1) return etat as SessionSuivisState
        return { ...etat, centrerSurSuivis: true } as SessionSuivisState
      },
    },
  ),
)
