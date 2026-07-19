// File de saisie hors-ligne (Zustand) — E04US009, ADR-0037.
//
// Quand le réseau tombe, une saisie de volée ne doit pas être **perdue** ni bloquer le marqueur : on
// la met dans cette file, persistée dans le `localStorage`, et on la **rejoue à la reconnexion**. La
// persistance vaut jusqu'au bout : la file survit à la fermeture de l'onglet (D-05 : pas de kiosque,
// l'onglet se ferme) comme la session de poste — un score en attente n'est pas perdu si la tablette
// est rouverte avant que le réseau revienne.
//
// Défini ici, dans `shared/`, pour que l'**indicateur de connexion** (`shared/realtime`) et la
// feature `saisie` en dépendent tous deux (et non l'inverse) — même parti que `sessionPosteStore`.
// Le **dédoublonnage** n'est pas ici : il est **serveur** (registre d'idempotence, ADR-0036), garanti
// tant que l'`identifiant_saisie` reste **stable au fil des rejeux** — d'où la règle « on fige
// l'identifiant à la mise en file, jamais à chaque tentative » (cf. `useRejeuFileHorsLigne`).

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// Le corps d'une saisie de volée en attente. Structurellement identique à `SaisirVolee` de
// `features/saisie/api` (la feature y passe ses corps sans que `shared/` importe la feature) : la file
// est agnostique de la façon dont la volée sera renvoyée, elle ne détient que de la donnée.
export interface VoleeEnFile {
  tournoi_id: number
  archer_id: number
  numero: number
  valeurs: string[]
  saisie_par: string | null
  identifiant_saisie: string
}

// Deux saisies visent la **même volée** (même triplet cible/archer/numéro) : une ré-édition hors-ligne
// remplace la précédente en attente plutôt que d'empiler deux corps pour le même emplacement (le
// serveur ferait de toute façon un « dernier écrit gagne » sur ce numéro — autant ne rejouer qu'une).
function memeVolee(a: VoleeEnFile, b: VoleeEnFile): boolean {
  return a.tournoi_id === b.tournoi_id && a.archer_id === b.archer_id && a.numero === b.numero
}

// Ajoute `corps` en fin de file (FIFO) en retirant une éventuelle attente pour la **même** volée.
// Pur (exporté pour test).
export function remplacerOuAjouter(
  file: readonly VoleeEnFile[],
  corps: VoleeEnFile,
): VoleeEnFile[] {
  return [...file.filter((c) => !memeVolee(c, corps)), corps]
}

interface FileHorsLigneState {
  enAttente: VoleeEnFile[]
  // Vrai pendant qu'un rejeu vide la file : l'indicateur affiche alors « Synchronisation… ».
  synchronisation: boolean
  mettreEnFile: (corps: VoleeEnFile) => void
  // Une saisie a été rejouée avec succès (ou refusée définitivement par le serveur) : on la retire.
  confirmer: (identifiantSaisie: string) => void
  demarrerSync: () => void
  terminerSync: () => void
}

export const useFileHorsLigneStore = create<FileHorsLigneState>()(
  persist(
    (set) => ({
      enAttente: [],
      synchronisation: false,
      mettreEnFile: (corps) =>
        set((etat) => ({ enAttente: remplacerOuAjouter(etat.enAttente, corps) })),
      confirmer: (identifiantSaisie) =>
        set((etat) => ({
          enAttente: etat.enAttente.filter((c) => c.identifiant_saisie !== identifiantSaisie),
        })),
      demarrerSync: () => set({ synchronisation: true }),
      terminerSync: () => set({ synchronisation: false }),
    }),
    {
      name: 'kervignarc-file-hors-ligne',
      // On ne persiste **que** la file, pas l'indicateur de synchronisation en cours : au rechargement,
      // aucun rejeu ne tourne encore (il repartira à la première reconnexion).
      partialize: (etat) => ({ enAttente: etat.enAttente }),
    },
  ),
)
