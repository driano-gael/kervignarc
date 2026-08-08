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
  /** La bascule « mes archers / tout » de l'appli publique (E16US004).
   *
   * **Une préférence de lecture, donc globale** — pas par tournoi, contrairement aux suivis :
   * « je regarde mes archers » se dit une fois et vaut partout. C'est `focus.modeEffectif` qui la
   * retombe sur « tout » lorsqu'on ouvre un tournoi où l'on ne suit personne (sans quoi tous les
   * écrans publics seraient vides sans que rien ne l'explique).
   *
   * Persistée avec la liste : elle survit à un rechargement, ce qui compte sur un téléphone qu'on
   * range et ressort toute la journée. Une clé absente du `localStorage` d'hier retombe sur la
   * valeur initiale par la fusion de `persist` — aucune migration à écrire.
   *
   * ⚠️ **Armée par défaut** (`true`), arbitrage du 08/08/2026 en revue d'E16US004. Le CA
   * d'E07US005 promet que « la lecture *Mon chemin* est celle par défaut **dès qu'on suit
   * quelqu'un** », et D-09 ouvre déjà l'onglet « Suivi » d'office pour la même raison : qui a
   * désigné ses archers a dit ce qu'il venait regarder. L'interrupteur unique d'E16US004 ayant
   * dissous les défauts **par vue**, laisser celui-ci sur `false` révoquait ce CA en silence.
   * C'est `focus.modeEffectif` qui rend la valeur inoffensive quand on ne suit personne — armée ne
   * veut donc pas dire « écran vide », jamais.
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
    { name: 'kervignarc-session-suivis' },
  ),
)
