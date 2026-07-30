// Présentation du panneau de routage (E04US018) — logique pure, testée en node (comme les autres
// `presentation.ts` des features).
//
// Le serveur dit **ce qui est** (issue, cible, rang, motif) ; ici on en fait la phrase que lit un
// archer entre deux volées, debout, avec son arc à la main. Trois règles tenues par ces fonctions :
//
// 1. **La destination d'abord.** « Cible 4 · place B » est l'information qu'il est venu chercher ;
//    le reste (tour, adversaire) est du contexte.
// 2. **Ce qui manque est dit, jamais laissé en blanc** (arbitrage de cadrage du 30/07/2026) : un
//    champ vide se lit comme une panne, une phrase se lit comme une attente. Les motifs viennent du
//    serveur — les quatre canaux de routage (`D-09`) doivent dire la même chose.
// 3. **Aucun rang inventé.** Le tableau ne sait attribuer que les rangs 1-4 (podium) ; les rangs
//    intermédiaires sont E06US004. Un battu sans rang lit où il est sorti, pas un chiffre faux.

import type { ProchainDuel, RoutageArcher } from './api'

// « Cible 4 · place B », ou `null` si la cible n'est pas encore attribuée (tour ≥ 2, ou plan de
// duels non matérialisé) — le panneau affiche alors `manque` à la place.
export function destination(prochain: ProchainDuel): string | null {
  if (prochain.cible === null) return null
  const place = prochain.position !== null ? ` · place ${prochain.position}` : ''
  return `Cible ${prochain.cible}${place}`
}

// Qui il affronte : le nom si le duel amont est tranché, sinon **quel duel** on attend.
export function adversaire(prochain: ProchainDuel): string {
  if (prochain.adversaire !== null) {
    return `${prochain.adversaire.nom} ${prochain.adversaire.prenom}`.trim()
  }
  if (prochain.sources_en_attente.length > 0) {
    const numeros = prochain.sources_en_attente.map((n) => `n°${n}`).join(', ')
    return `en attente du duel ${numeros}`
  }
  return 'adversaire non déterminé'
}

// Le rang de podium en toutes lettres — « Vainqueur du tableau », « 2ᵉ », « 3ᵉ »… `null` tant que
// le rang n'est pas acquis (le panneau affiche alors le tour de sortie et le motif).
export function rang(archer: RoutageArcher): string | null {
  if (archer.rang_final === null) return null
  if (archer.rang_final === 1) return 'Vainqueur du tableau'
  return `${archer.rang_final}ᵉ du tableau`
}

// La ligne principale d'un archer : ce qu'il doit retenir en une seconde.
export function titre(archer: RoutageArcher): string {
  if (archer.issue === 'prochain_duel' && archer.prochain !== null) {
    return destination(archer.prochain) ?? archer.prochain.libelle
  }
  if (archer.issue === 'termine') {
    const place = rang(archer)
    if (place !== null) return place
    return archer.tour_sortie !== null ? `Éliminé — ${archer.tour_sortie}` : 'Éliminé'
  }
  return 'Destination inconnue'
}

// L'avertissement à afficher **en plus** de la destination, ou `null`. Distinct de `detail` : celui-ci
// dit ce qu'on sait, celui-là ce dont il faut se méfier (le duel n'est pas côte à côte).
export function alerte(archer: RoutageArcher): string | null {
  return archer.issue === 'prochain_duel' ? (archer.prochain?.alerte ?? null) : null
}

// La ligne secondaire : le contexte, ou **l'attente nommée** quand l'information n'existe pas encore.
export function detail(archer: RoutageArcher): string | null {
  if (archer.issue === 'prochain_duel' && archer.prochain !== null) {
    const contexte = `${archer.prochain.libelle} · ${adversaire(archer.prochain)}`
    // Cible inconnue : le titre a déjà pris le libellé du tour, on ne le répète pas — on annonce
    // l'attente (« cible attribuée au lancement du tour »).
    // `manque` est garanti non nul par le serveur quand il n'y a pas de cible (c'est lui qui sait
    // *pourquoi* : tour à venir, ou plan non matérialisé) — pas de repli local à inventer.
    return destination(archer.prochain) === null
      ? `${archer.prochain.manque} · ${adversaire(archer.prochain)}`
      : contexte
  }
  return archer.motif
}

// Le panneau bascule tout seul quand **tous** les archers de la cible ont fini de tirer (CA : « dès
// la validation »). Une série est finie quand elle est complète **et** verrouillée par le scoreur :
// un tir non validé ne compte pas — c'est le scoreur qui clôt, pas le marqueur.
//
// `forfait` clôt aussi, et c'est indispensable : un archer qui abandonne ou est disqualifié
// (E04US015) **reste dans la grille** avec une série incomplète pour toujours. Sans cette clause,
// `cibleClose` ne serait jamais vrai et les trois autres archers de la cible perdraient le panneau.
// C'est le serveur qui porte le signal (`LigneGrille.forfait`) — même notion que la complétude
// (« barème validé **ou** forfait », DETTE-014) : le front n'a pas à la re-dériver.
// Le panneau bascule tout seul quand **tous** les archers de la cible ont fini de tirer (CA : « dès
// la validation »). Une série est finie quand elle est complète **et** verrouillée par le scoreur :
// un tir non validé ne compte pas — c'est le scoreur qui clôt, pas le marqueur.
//
// `forfait` clôt aussi, et c'est indispensable : un archer qui abandonne ou est disqualifié
// (E04US015) **reste dans la grille** avec une série incomplète pour toujours. Sans cette clause,
// `cibleClose` ne serait jamais vrai et les trois autres archers de la cible perdraient le panneau.
// C'est le serveur qui porte le signal (`LigneGrille.forfait`) — même notion que la complétude
// (« barème validé **ou** forfait », DETTE-014) : le front n'a pas à la re-dériver.
// Le panneau s'ouvre **tout seul** quand la cible a fini (CA), et se rouvre **à la main** à tout
// moment. Trois entrées, et le piège est dans leur composition : refermer une ouverture *manuelle*
// ne doit pas consommer l'ouverture *automatique* à venir. Sans cette distinction, jeter un œil au
// panneau en cours de saisie éteint silencieusement la bascule de fin de cible — c'est-à-dire le CA
// central de l'US. Logique pure et testée pour cette raison précise.
export function panneauOuvert(etat: {
  cibleClose: boolean
  ferme: boolean
  force: boolean
}): boolean {
  return etat.force || (etat.cibleClose && !etat.ferme)
}

// Ce que « Retour » laisse derrière lui : on ne marque « déjà vu » que si le panneau s'était ouvert
// **de lui-même**. Fermer une consultation manuelle laisse la bascule automatique armée.
export function apresRetour(etat: { cibleClose: boolean }): { ferme: boolean; force: boolean } {
  return { ferme: etat.cibleClose, force: false }
}

export function serieClose(
  volees: { verrouillee: boolean }[],
  nbVolees: number | null,
  forfait = false,
): boolean {
  if (forfait) return true
  if (nbVolees === null || volees.length < nbVolees) return false
  return volees.every((volee) => volee.verrouillee)
}
