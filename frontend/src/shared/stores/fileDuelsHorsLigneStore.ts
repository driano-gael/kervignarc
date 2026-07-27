// File de saisie **de duels** hors-ligne (Zustand) — E04US013, résilience E04US009 / ADR-0037.
//
// Quand le réseau tombe pendant qu'un scoreur score un duel, l'acte (saisir une manche, un barrage,
// valider) ne doit pas être **perdu** ni bloquer le scoreur : on le met dans cette file, persistée
// dans le `localStorage`, et on le **rejoue à la reconnexion**. Jumeau de `fileHorsLigneStore` (la
// qualif) — **2ᵉ occurrence** du motif : on **duplique** plutôt que d'extraire un socle générique
// (règle 12 / § Dette : la 3ᵉ occurrence déclenchera l'extraction en ADR + US dédiée, pas avant).
//
// **Divergence assumée avec la file de qualification** : ici la file est **FIFO stricte, sans dédup
// à l'enfilage**. La qualif remplace une volée en attente de même emplacement (actes homogènes,
// emplacements indépendants) ; un duel enchaîne des actes **hétérogènes dont l'ordre compte** —
// valider suppose les manches déjà rejouées. Réordonner une manche rééditée après la validation la
// ferait rejouer sur un duel « déjà tranché » (refus). On garde donc l'ordre d'action = ordre de
// rejeu. Le **dédoublonnage** reste **serveur** (idempotence par `identifiant_saisie`, ADR-0036),
// stable tant que l'identifiant est figé à l'enfilage (jamais régénéré au rejeu).

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// Les corps d'actes en attente. Structurellement identiques aux requêtes de `features/saisie-duels/
// api` (la feature y passe ses corps sans que `shared/` importe la feature — inversion de
// dépendance, comme `VoleeEnFile`). Discriminés par `type` pour le rejeu (endpoint par acte).
export interface MancheEnFile {
  type: 'manche'
  tournoi_id: number
  phase_id: number
  match_numero: number
  numero: number
  valeurs_haut: string[]
  valeurs_bas: string[]
  identifiant_saisie: string
}

export interface BarrageEnFile {
  type: 'barrage'
  tournoi_id: number
  phase_id: number
  match_numero: number
  fleche_haut: string
  fleche_bas: string
  gagnant_designe: 'haut' | 'bas' | null
  identifiant_saisie: string
}

export interface ValidationEnFile {
  type: 'validation'
  tournoi_id: number
  phase_id: number
  match_numero: number
  identifiant_saisie: string
}

export type ActeDuelEnFile = MancheEnFile | BarrageEnFile | ValidationEnFile

// Clé d'**emplacement** d'un acte (pas d'identité de geste) : sert à retirer de la file les actes
// qu'une saisie **en ligne** réussie du même emplacement a rendus obsolètes (supersession, cf.
// `retirerSlot`). Une manche est scopée par son rang ; barrage et validation par le match. Pure.
export function cleSlot(acte: ActeDuelEnFile): string {
  const base = `${acte.type}:${acte.tournoi_id}:${acte.phase_id}:${acte.match_numero}`
  return acte.type === 'manche' ? `${base}:${acte.numero}` : base
}

interface FileDuelsHorsLigneState {
  enAttente: ActeDuelEnFile[]
  // Vrai pendant qu'un rejeu vide la file : l'indicateur affiche « Synchronisation… ».
  synchronisation: boolean
  // FIFO strict : on **ajoute en fin**, sans retirer un acte de même emplacement (voir l'en-tête —
  // l'ordre d'action doit être préservé pour le rejeu).
  mettreEnFile: (acte: ActeDuelEnFile) => void
  // Un acte a été rejoué avec succès (ou refusé définitivement par le serveur) : on le retire.
  confirmer: (identifiantSaisie: string) => void
  // Une saisie **en ligne** a réussi pour cet emplacement : elle fait autorité et supersède les actes
  // en attente du **même** emplacement (retirés pour ne pas réécraser la valeur neuve au rejeu ; un
  // rejeu déjà en vol relit l'appartenance vivante avant chaque envoi et saute ce qui a été retiré).
  retirerSlot: (cle: string) => void
  demarrerSync: () => void
  terminerSync: () => void
}

export const useFileDuelsHorsLigneStore = create<FileDuelsHorsLigneState>()(
  persist(
    (set) => ({
      enAttente: [],
      synchronisation: false,
      mettreEnFile: (acte) => set((etat) => ({ enAttente: [...etat.enAttente, acte] })),
      confirmer: (identifiantSaisie) =>
        set((etat) => ({
          enAttente: etat.enAttente.filter((a) => a.identifiant_saisie !== identifiantSaisie),
        })),
      retirerSlot: (cle) =>
        set((etat) => ({ enAttente: etat.enAttente.filter((a) => cleSlot(a) !== cle) })),
      demarrerSync: () => set({ synchronisation: true }),
      terminerSync: () => set({ synchronisation: false }),
    }),
    {
      name: 'kervignarc-file-duels-hors-ligne',
      // On ne persiste **que** la file, pas le drapeau de synchronisation (aucun rejeu ne tourne au
      // rechargement : il repartira à la première reconnexion).
      partialize: (etat) => ({ enAttente: etat.enAttente }),
    },
  ),
)
