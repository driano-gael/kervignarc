// Présentation du panneau de routage (E04US018) — logique pure, testée en node.
//
// Le serveur dit **ce qui est** ; ici on en fait la phrase que lit un archer entre deux volées.
// Trois règles : la **destination d'abord** (« Cible 4 · couloir B »), le reste est du contexte ;
// **ce qui manque est dit, jamais laissé en blanc** (arbitrage du 30/07/2026 — un champ vide se lit
// comme une panne), les motifs venant du serveur pour que les quatre canaux (`D-09`) disent la même
// chose ; **aucun rang inventé** — on affiche la **fourchette** acquise (« 5ᵉ-8ᵉ », E07US008).

import { nommerType } from '../../shared/phases/catalogue'
import type { IssueRoutage, ProchainDuel, RoutageArcher } from './api'

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
// ⚠️ **On partitionne sur l'ISSUE, jamais sur la cible.** Le serveur ne pose une cible qu'au **tour
// 1** (`DETTE-019`) : partitionner sur `prochain?.cible` rangeait dès le tour 2 tous les archers
// encore en lice — demi-finalistes compris — parmi les **sortis**. Laissée dans le composant, la
// correction n'avait aucun filet. Trois groupes car il y a trois situations : posé sur une butte,
// en lice sans butte attribuée, sorti du tableau.
export function partitionner(archers: RoutageArcher[]): {
  poses: RoutageArcher[]
  attente: RoutageArcher[]
  sortis: RoutageArcher[]
} {
  // ⚠️ `prochaine_manche` compte ici (E05US028) : sur un Big Shoot Off les finalistes **sont** le
  // pas de tir, et ne tester que `prochain_duel` les rangeait sous « Sortis » sur l'écran projeté
  // pendant toute la finale. ⚠️ `en_attente` aussi (E05US030) : l'archer qui porte le bye d'une
  // ronde n'a aucune cible à cet instant et en aura une à la suivante. Faute de rendez-vous connu
  // (`DETTE-059` pour le BSO), ils tombent en **attente**, avec le motif du serveur.
  const enLice = (l: RoutageArcher) =>
    l.issue === 'prochain_duel' || l.issue === 'prochaine_manche' || l.issue === 'en_attente'
  const cible = (l: RoutageArcher) =>
    l.issue === 'prochaine_manche' ? l.prochaine_manche?.cible : l.prochain?.cible
  return {
    poses: archers.filter((l) => enLice(l) && cible(l) != null),
    attente: archers.filter((l) => enLice(l) && cible(l) == null),
    // `indisponible` atterrit ici. Injoignable sur ce canal — la vue collective n'itère que sur les
    // occupants du tableau, donc `_router` ne peut pas rendre « non retenu » — mais si cela changeait,
    // « sorti » reste la lecture la moins fausse.
    sortis: archers.filter((l) => !enLice(l)),
  }
}

// Le pas de tir en mode « mes archers » (E16US004) — **logique pure, donc testable**.
//
// ⚠️ **La butte reste entière, adversaire compris** — règle posée par `shared/suivis/focus.ts`, et
// qui compte davantage ici : sur un tableau de duels, le voisin de butte **est** l'adversaire.
// Filtré ligne à ligne, « Cible 7 · B · MARTIN Luc » ne disait plus contre qui Luc tire. Le bloc ne
// rend pas le champ `adversaire` : c'est le **voisinage** qui porte l'appariement. Ne concerne que
// la lecture « par cible » — les sections annexes restent centrées sur les seuls archers suivis.
export function posesParCible(
  posesCentrees: RoutageArcher[],
  tousLesArchers: RoutageArcher[],
  centre: boolean,
): RoutageArcher[] {
  if (!centre) return partitionner(tousLesArchers).poses
  const ciblesSuivies = new Set(
    posesCentrees.map((ligne) => ligne.prochain?.cible).filter((cible) => cible != null),
  )
  return partitionner(tousLesArchers).poses.filter(
    (ligne) => ligne.prochain?.cible != null && ciblesSuivies.has(ligne.prochain.cible),
  )
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
  // Le rendez-vous d'un finaliste de Big Shoot Off (E05US028). Sans cette branche, l'issue tombait
  // dans le repli et les huit finalistes lisaient « Destination inconnue » sur les quatre canaux —
  // le CA « le routage sait où l'archer tire ensuite » n'était pas délivré côté utilisateur, alors
  // que trois tests backend et `route_l_archer=True` affirmaient le contraire.
  if (archer.issue === 'prochaine_manche' && archer.prochaine_manche !== null) {
    return `Manche ${archer.prochaine_manche.numero}`
  }
  if (archer.issue === 'termine') {
    const place = rang(archer)
    if (place !== null) return place
    return archer.tour_sortie !== null ? `Éliminé — ${archer.tour_sortie}` : 'Éliminé'
  }
  // ⚠️ **« Rien à tirer pour l'instant » n'est pas « terminé »** (E05US030). Le titre doit dire
  // l'attente et rien d'autre : le *pourquoi* est dans le motif du serveur, que `detail` rend. Un
  // titre qui annoncerait « Ronde suivante » promettrait un rendez-vous qui n'est pas encore
  // apparié — les adversaires se choisissent au classement du moment.
  if (archer.issue === 'en_attente') return 'Rien à tirer pour l’instant'
  return 'Destination inconnue'
}

// L'avertissement à afficher **en plus** de la destination, ou `null`. Distinct de `detail` : celui-ci
// dit ce qu'on sait, celui-là ce dont il faut se méfier (le duel n'est pas côte à côte).
export function alerte(archer: RoutageArcher): string | null {
  return archer.issue === 'prochain_duel' ? (archer.prochain?.alerte ?? null) : null
}

// L'archer a-t-il encore quelque chose à jouer ? Un repêché **oui**, même sans duel affiché : il
// est sorti de ce tableau, pas de la compétition. ⚠️ **Le `Record` indexé par `IssueRoutage` est le
// garde-fou d'exhaustivité de ce module** (E05US028) : il fait **échouer la compilation** quand le
// serveur publie une issue de plus. Sans lui `tsc` est aveugle — les issues arrivent castées par
// `fetchJson`, et une chaîne de `===` se contente d'un repli silencieux. C'est ce qui s'est produit
// pour `prochaine_manche` : livrée côté serveur, jamais lue côté front.
const EN_LICE: Record<IssueRoutage, boolean> = {
  prochain_duel: true,
  // Un finaliste de Big Shoot Off a une manche devant lui : le ranger avec les sortis le ferait
  // rentrer chez lui au milieu de la finale (E05US028).
  prochaine_manche: true,
  // Un repêché est sorti de **ce tableau**, pas de la compétition (E07US008).
  repeche: true,
  // Le porteur d'un bye, ou celui dont la rencontre vient d'être validée pendant que la ronde
  // s'achève (E05US030). Il tirera la ronde suivante : le ranger avec les sortis le ferait rentrer
  // chez lui **au milieu** de la phase. C'est ce que l'emprunt d'`indisponible` faisait
  // jusqu'ici — la valeur ne disait rien de faux, mais elle le comptait du mauvais côté.
  en_attente: true,
  termine: false,
  indisponible: false,
}

export function encoreEnLice(archer: RoutageArcher): boolean {
  return EN_LICE[archer.issue]
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
  if (archer.issue === 'prochaine_manche' && archer.prochaine_manche !== null) {
    // Combien sortent à ce tour — l'information qui compte pour le tireur, davantage que le numéro
    // de la manche déjà porté par le titre. `manque` reprend la main pour dire que la cible n'est
    // pas connue (`DETTE-059`), au lieu de laisser un blanc qui se lirait comme une panne.
    const sortants = archer.prochaine_manche.elimine
    const combien = `${sortants} archer${sortants > 1 ? 's' : ''} ${sortants > 1 ? 'sortent' : 'sort'}`
    const manque = archer.prochaine_manche.manque
    return manque !== null ? `${combien} · ${manque}` : combien
  }
  if (archer.issue === 'termine' && archer.motif === null && rang(archer) !== null) {
    return archer.tour_sortie
  }
  return archer.motif
}

// Le panneau bascule tout seul quand **tous** les archers de la cible ont fini (CA « dès la
// validation ») : une série est finie quand elle est complète **et** verrouillée par le scoreur. ⚠️
// `forfait` clôt aussi, et c'est indispensable : un archer qui abandonne **reste dans la grille**
// avec une série incomplète pour toujours, donc sans cette clause `cibleClose` ne serait jamais
// vrai et les trois autres archers perdraient le panneau (signal serveur, même notion que la
// complétude — `DETTE-014`). Il se rouvre **à la main** à tout moment : refermer une ouverture
// *manuelle* ne doit pas consommer l'ouverture *automatique* à venir, sans quoi jeter un œil au
// panneau éteint le CA central de l'US.
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
