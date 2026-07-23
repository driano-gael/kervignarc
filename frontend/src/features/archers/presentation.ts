// Présentation des doublons détectés (E02US005) — logique **pure** (testée sans rendu, E00US014).
//
// Le serveur renvoie les paires déjà triées (probable avant à vérifier). Ici on ne fait que les
// **répartir sous un titre lisible** — aucune règle métier, qui vit côté domaine Python
// (`domain/doublons.py`).

import type { Doublon } from './api'

// Les deux niveaux du serveur, du plus sûr au plus douteux, avec leur titre d'écran. L'ordre de ce
// tableau **est** l'ordre d'affichage des groupes.
const NIVEAUX = [
  { niveau: 'probable', libelle: 'Doublons probables' },
  { niveau: 'a_verifier', libelle: 'À vérifier' },
] as const

export interface GroupeDoublons {
  niveau: string
  libelle: string
  paires: Doublon[]
}

// Regroupe les paires par niveau, dans l'ordre « probable » puis « à vérifier », en n'émettant que
// les groupes **non vides** — un titre sans paire en dessous n'a rien à dire. Un niveau inconnu
// (serveur en avance sur le front) n'apparaît pas : le front et le back évoluent ensemble.
export function grouperDoublons(doublons: Doublon[]): GroupeDoublons[] {
  return NIVEAUX.map(({ niveau, libelle }) => ({
    niveau,
    libelle,
    paires: doublons.filter((doublon) => doublon.niveau === niveau),
  })).filter((groupe) => groupe.paires.length > 0)
}
