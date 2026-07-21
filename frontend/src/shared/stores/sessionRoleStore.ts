// Rôle d'entrée choisi sur cet appareil (Zustand) — E00US017, ADR-0042.
//
// Porte le **seul marqueur du choix explicite** fait à l'écran d'accueil (Tablette / Public /
// Scoreur / Admin), persisté dans le `localStorage` pour que l'app aille **droit** au bon monde aux
// ouvertures suivantes, sans réafficher l'écran de choix (D-09 : pas de friction récurrente). Ce
// marqueur est **distinct** des jetons de session (poste, admin, scoreur), qui portent l'auth *dans*
// un rôle ; ici on ne mémorise que « quelle porte cet appareil a franchie ». La résolution du rôle
// **effectif** (une session en cours prime sur le choix) vit dans `app/resoudreRole.ts`.

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// Les quatre portes de l'écran d'accueil. Vocabulaire d'appareil/usage côté français, cohérent avec
// le CDC UX (Tablette de cible, Téléphone public, Scoreur, Admin).
export type Role = 'tablette' | 'public' | 'scoreur' | 'admin'

interface SessionRoleState {
  role: Role | null
  // Choix explicite d'une porte à l'écran d'accueil.
  choisir: (role: Role) => void
  // « Changer de rôle » : oublie le choix → l'app réaffiche l'écran de choix. La purge des jetons de
  // session (poste/admin/scoreur) est faite par l'appelant (`ChangerDeRole`), sans quoi la résolution
  // ré-inférerait le rôle depuis un jeton résiduel (cf. ADR-0042).
  reinitialiser: () => void
}

export const useSessionRoleStore = create<SessionRoleState>()(
  persist(
    (set) => ({
      role: null,
      choisir: (role) => set({ role }),
      reinitialiser: () => set({ role: null }),
    }),
    { name: 'kervignarc-role' },
  ),
)
