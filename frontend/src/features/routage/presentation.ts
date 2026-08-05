// Présentation du panneau de routage (E04US018) — logique pure, testée en node (comme les autres
// `presentation.ts` des features).
//
// Le serveur dit **ce qui est** (issue, cible, rang, motif) ; ici on en fait la phrase que lit un
// archer entre deux volées, debout, avec son arc à la main. Trois règles tenues par ces fonctions :
//
// 1. **La destination d'abord.** « Cible 4 · couloir B » est l'information qu'il est venu chercher ;
//    le reste (tour, adversaire) est du contexte.
// 2. **Ce qui manque est dit, jamais laissé en blanc** (arbitrage de cadrage du 30/07/2026) : un
//    champ vide se lit comme une panne, une phrase se lit comme une attente. Les motifs viennent du
//    serveur — les quatre canaux de routage (`D-09`) doivent dire la même chose.
// 3. **Aucun rang inventé.** Un rang unique hors podium n'existe pas dans un tableau tronqué — on
//    affiche donc la **fourchette** acquise (« 5ᵉ-8ᵉ », E07US008), jamais un chiffre choisi au
//    hasard dedans. Le classement officiel, agrégé entre phases, reste E06US004.

import { nommerType } from '../../shared/phases/catalogue'
import type { ProchainDuel, RoutageArcher } from './api'

// « Cible 4 · couloir B », ou `null` si la cible n'est pas encore attribuée (tour ≥ 2, ou plan de
// duels non matérialisé) — le panneau affiche alors `manque` à la place.
export function destination(prochain: ProchainDuel): string | null {
  if (prochain.cible === null) return null
  const couloir = prochain.position !== null ? ` · couloir ${prochain.position}` : ''
  return `Cible ${prochain.cible}${couloir}`
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

// Le rang acquis en toutes lettres — « Vainqueur du tableau », « 2ᵉ du tableau », « 5ᵉ-8ᵉ du
// tableau »… `null` tant que rien n'est acquis (le panneau affiche alors le tour de sortie).
//
// La **fourchette** n'est pas un pis-aller (E07US008) : dans un tableau tronqué au podium, les
// quatre battus des quarts sont 5ᵉ-8ᵉ *ex æquo* et aucun match ne les départage. Annoncer un chiffre
// unique serait faux ; ne rien annoncer, ce que faisait le panneau avant cette US, n'apprenait rien
// à quelqu'un qui vient de perdre.
export function rang(archer: RoutageArcher): string | null {
  if (archer.rang_final === 1) return 'Vainqueur du tableau'
  if (archer.rang_final !== null) return `${archer.rang_final}ᵉ du tableau`
  if (archer.rang_min === null || archer.rang_max === null) return null
  if (archer.rang_min === archer.rang_max) return `${archer.rang_min}ᵉ du tableau`
  return `${archer.rang_min}ᵉ-${archer.rang_max}ᵉ du tableau`
}

// Où va un repêché — « Repêché → 3. Élimination directe ». Sans destination : un trou de
// composition (aucune phase ne prélève ces battus), que `motif` explicite.
export function repechage(
  archer: RoutageArcher,
  nommer: (type: string) => string = nommerType,
): string {
  if (archer.destination === null) return 'Repêché'
  return `Repêché → ${archer.destination.ordre}. ${nommer(archer.destination.type)}`
}

// Les trois groupes d'un panneau d'affectations — **logique pure, donc testable**.
//
// ⚠️ **On partitionne sur l'ISSUE, jamais sur la cible.** Le serveur ne pose une cible qu'au
// **tour 1** (garde tour-1, `DETTE-019`) : partitionner sur `prochain?.cible` rangeait, dès le
// tour 2, tous les archers encore en lice — demi-finalistes compris — parmi les **sortis**. C'était
// le bloquant de la revue, et cette fonction existe pour qu'il ne puisse pas revenir en silence :
// laissée dans le composant, la correction n'avait aucun filet (remarque de la 2ᵉ passe).
//
// Trois groupes parce qu'il y a trois situations, et non deux : posé sur une butte, en lice sans
// butte encore attribuée, sorti du tableau.
export function partitionner(archers: RoutageArcher[]): {
  poses: RoutageArcher[]
  attente: RoutageArcher[]
  sortis: RoutageArcher[]
} {
  const enLice = (l: RoutageArcher) => l.issue === 'prochain_duel'
  return {
    poses: archers.filter((l) => enLice(l) && l.prochain?.cible != null),
    attente: archers.filter((l) => enLice(l) && l.prochain?.cible == null),
    // `indisponible` atterrit ici. Injoignable sur ce canal — la vue collective n'itère que sur les
    // occupants du tableau, donc `_router` ne peut pas rendre « non retenu » — mais si cela changeait,
    // « sorti » reste la lecture la moins fausse.
    sortis: archers.filter((l) => !enLice(l)),
  }
}

// La ligne principale d'un archer : ce qu'il doit retenir en une seconde.
//
// ⚠️ Le défaut de `nommer` est le **vrai** catalogue, pas l'identité (correctif de revue). Un repli
// identité rendait l'oubli d'un appelant silencieux : `PanneauRoutage` (canal n°1) appelait
// `titre(ligne)` tout court et aurait affiché « Repêché → 3. **elimination_directe** » — la valeur
// d'énumération brute — alors que l'US répète que les quatre canaux disent la même chose.
export function titre(
  archer: RoutageArcher,
  nommer: (type: string) => string = nommerType,
): string {
  if (archer.issue === 'prochain_duel' && archer.prochain !== null) {
    return destination(archer.prochain) ?? archer.prochain.libelle
  }
  // Un repêché **avant** un éliminé, et jamais confondu avec lui : il n'a pas de rang et n'a pas
  // fini. Lui afficher « Éliminé » le ferait rentrer chez lui avant son duel.
  if (archer.issue === 'repeche') return repechage(archer, nommer)
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

// L'archer a-t-il encore quelque chose à jouer ? Un repêché **oui**, même sans duel affiché : il est
// sorti de ce tableau, pas de la compétition. Sert aux surfaces qui distinguent « en lice » de
// « fini » (couleur, tri) — la distinction est métier, pas décorative, d'où sa place ici.
export function encoreEnLice(archer: RoutageArcher): boolean {
  return archer.issue === 'prochain_duel' || archer.issue === 'repeche'
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
  // Un repêché a une destination en titre : le détail dit **d'où** il vient (le tour qu'il a perdu),
  // sans quoi « Repêché → phase 3 » ne se rattache à rien de ce qu'il vient de vivre. Le `motif`
  // reprend la main quand il n'y a pas de destination — c'est alors la seule chose à dire.
  if (archer.issue === 'repeche') return archer.motif ?? archer.tour_sortie
  if (archer.issue === 'termine' && archer.motif === null && rang(archer) !== null) {
    return archer.tour_sortie
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
