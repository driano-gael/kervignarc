// Logique pure de la saisie en duels (E04US013) — libellés, avancement, injection optimiste.
//
// Isolée du rendu React pour être **testée** (vitest en node, sans DOM). Le serveur reste
// l'**autorité** (mode, barème, zones, **résultat** — ADR-0049 : le front ne recompute pas l'issue
// d'un duel) : ces fonctions ne pilotent que l'affichage — total provisoire d'une volée en frappe,
// quelle manche saisir, libellé du tour, et l'état **optimiste** d'un duel dont un acte est en file
// hors-ligne (pour que le scoreur continue au lieu de rester bloqué).

import type { Duel, ModeDuel, SaisirBarrage, SaisirManche } from './api'

// Points d'une valeur de zone (jumeau de `features/saisie/volees.pointsZone`, 2ᵉ occurrence — règle
// 12 : duplication assumée, pas d'extraction avant un 3ᵉ cas). `M` (manqué) = 0, sinon la valeur.
export function pointsZone(valeur: string): number {
  if (valeur === 'M') return 0
  const points = Number.parseInt(valeur, 10)
  return Number.isNaN(points) ? 0 : points
}

// Total provisoire d'une volée en cours de frappe (retour visuel immédiat, avant enregistrement).
export function totalVolee(valeurs: readonly string[]): number {
  return valeurs.reduce((somme, valeur) => somme + pointsZone(valeur), 0)
}

// Libellé du mode d'un duel affiché au scoreur (D-11 : dire quoi saisir).
export function libelleMode(mode: ModeDuel | null): string {
  if (mode === 'cumul') return 'Cumul (arc à poulies)'
  if (mode === 'sets') return 'Système de sets'
  return ''
}

// La petite finale (place 3-4) **partage le dernier tour** avec la finale (côté domaine) : c'est le
// seul cas où deux matchs d'un même tour portent des libellés distincts. Prédicat isolé (utilisé par
// `libelleTour` et `grouperParTour`) pour ne pas dupliquer le test.
export function estPetiteFinale(duel: Pick<Duel, 'place_en_jeu'>): boolean {
  const place = duel.place_en_jeu
  return place !== null && place[0] === 3 && place[1] === 4
}

// Libellé du tour d'un match. On raisonne en **distance à la finale** (`nb_tours - tour`) : le
// dernier tour est la finale (ou la « petite finale » pour la 3ᵉ place, place_en_jeu = 3-4), l'avant
// dernier les demies, etc. Au-delà des quarts, on nomme la fraction (1/8, 1/16…). Le placement
// (`place_en_jeu`) prime pour distinguer finale et petite finale, qui partagent le dernier tour.
// DETTE-020 : le domaine calcule **aussi** ce libellé (`domain/tableau.py:libelle_tour`,
// E04US018), au singulier et sans suffixe sur la petite finale — deux domiciles pour une règle
// de vocabulaire (ADR-0006). À unifier côté serveur, le front consommera son libellé.
export function libelleTour(duel: Pick<Duel, 'tour' | 'place_en_jeu'>, nbTours: number): string {
  if (estPetiteFinale(duel)) return 'Petite finale (3ᵉ place)'
  const distance = nbTours - duel.tour
  switch (distance) {
    case 0:
      return 'Finale'
    case 1:
      return 'Demi-finales'
    case 2:
      return 'Quarts de finale'
    default:
      return `1/${2 ** distance} de finale`
  }
}

// Regroupe les duels d'un tableau **par libellé de tour**, dans l'ordre de lecture : tour décroissant
// (finale en tête), puis à tour égal la finale **avant** la petite finale. On groupe par le libellé
// (et non par le `tour` brut) sinon la petite finale, qui partage le dernier tour avec la finale, se
// rangerait sous l'en-tête « Finale ». Les duels consécutifs de même titre sont fusionnés (les deux
// demi-finales → une section « Demi-finales »). Logique pure — testée à part du rendu.
export function grouperParTour(
  duels: readonly Duel[],
  nbTours: number,
): { titre: string; duels: Duel[] }[] {
  const ordonnes = [...duels].sort(
    (a, b) => b.tour - a.tour || Number(estPetiteFinale(a)) - Number(estPetiteFinale(b)),
  )
  const groupes: { titre: string; duels: Duel[] }[] = []
  for (const duel of ordonnes) {
    const titre = libelleTour(duel, nbTours)
    const dernier = groupes[groupes.length - 1]
    if (dernier !== undefined && dernier.titre === titre) dernier.duels.push(duel)
    else groupes.push({ titre, duels: [duel] })
  }
  return groupes
}

// La prochaine manche à saisir : la **plus petite** (1..nbManches) pas encore saisie ; si toutes le
// sont, on reste sur la **dernière** (l'édition d'une manche déjà saisie passe par le navigateur,
// tant que le duel n'est pas validé). Jumeau de `volees.prochaineASaisir`.
export function prochaineMancheASaisir(duel: Pick<Duel, 'manches'>, nbManches: number): number {
  for (let numero = 1; numero <= nbManches; numero += 1) {
    if (!duel.manches.some((m) => m.numero === numero)) return numero
  }
  return Math.max(nbManches, 1)
}

// La manche déjà saisie portant ce numéro (pour pré-remplir les pavés lors d'une réédition), ou null.
export function mancheExistante(
  duel: Pick<Duel, 'manches'>,
  numero: number,
): { numero: number; haut: string[]; bas: string[] } | null {
  return duel.manches.find((m) => m.numero === numero) ?? null
}

// Adversaires connus (les deux camps résolus, hors bye) : condition d'un match **saisissable**.
export function adversairesConnus(duel: Pick<Duel, 'haut' | 'bas' | 'est_bye'>): boolean {
  return duel.haut !== null && duel.bas !== null && !duel.est_bye
}

// Duel **jouable** : adversaires connus **et** pavé déterminé (le serveur a résolu barème + zones).
export function estJouable(duel: Duel): boolean {
  return adversairesConnus(duel) && duel.nb_manches !== null && duel.zones.length > 0
}

// Statut d'un duel pour la liste (pur, testé). Ordre de priorité : un bye est exempt ; sans
// adversaires connus, rien à faire ; un duel validé est scellé ; un duel tranché non validé attend sa
// validation ; un duel entamé est en cours ; sinon il reste à saisir. Un acte en file l'annote « en
// attente » par-dessus (drapeau local `en_attente`), traité à part par l'UI.
export type StatutDuel =
  'bye' | 'attente_adversaires' | 'a_saisir' | 'en_cours' | 'a_valider' | 'valide'

export function statutDuel(duel: Duel): StatutDuel {
  if (duel.est_bye) return 'bye'
  if (!adversairesConnus(duel)) return 'attente_adversaires'
  if (duel.validee_par !== null) return 'valide'
  if (duel.resultat?.termine === true) return 'a_valider'
  if (duel.manches.length > 0 || duel.barrage !== null) return 'en_cours'
  return 'a_saisir'
}

// État **optimiste** d'un duel après une saisie de manche mise en file hors-ligne (E04US009) : faute
// d'accusé serveur, on injecte la manche localement (`en_attente`) pour que le navigateur **avance**
// au lieu de rester bloqué. Le **résultat** ne bouge pas : il reste l'autorité serveur (ADR-0049 : on
// ne recompute pas l'issue) — la vérité reviendra au rejeu (`invalidateQueries`). La manche remplace
// celle de même numéro si elle existait (réédition).
export function injecterManche(duel: Duel, corps: SaisirManche): Duel {
  const manche = { numero: corps.numero, haut: corps.valeurs_haut, bas: corps.valeurs_bas }
  const manches = [...duel.manches.filter((m) => m.numero !== corps.numero), manche].sort(
    (a, b) => a.numero - b.numero,
  )
  return { ...duel, manches, en_attente: true }
}

// État **optimiste** d'un duel après une saisie de barrage mise en file hors-ligne. Le barrage
// remplace un éventuel barrage précédent (réédition). Résultat inchangé (autorité serveur).
export function injecterBarrage(duel: Duel, corps: SaisirBarrage): Duel {
  return {
    ...duel,
    barrage: {
      haut: corps.fleche_haut,
      bas: corps.fleche_bas,
      gagnant_designe: corps.gagnant_designe,
    },
    en_attente: true,
  }
}

// Identifiant de saisie unique (idempotence ADR-0036), robuste **hors contexte sécurisé**.
// `crypto.randomUUID()` n'existe que sur HTTPS / `localhost` ; le déploiement jour J est un **LAN en
// http** (`http://<ip>`) où il est **absent** — la saisie casserait alors silencieusement.
// `crypto.getRandomValues` est disponible partout : on bâtit un UUID v4 dessus en repli. Jumeau de
// `features/saisie/volees.nouvelIdentifiant` (2ᵉ occurrence, règle 12 — même piège LAN-http, cf.
// mémoire ; extraction en `shared/` différée à un 3ᵉ cas, § Dette).
export function nouvelIdentifiant(): string {
  const c = globalThis.crypto
  if (typeof c.randomUUID === 'function') return c.randomUUID()
  const octets = c.getRandomValues(new Uint8Array(16))
  octets[6] = ((octets[6] ?? 0) & 0x0f) | 0x40 // version 4
  octets[8] = ((octets[8] ?? 0) & 0x3f) | 0x80 // variante RFC 4122
  const hex = Array.from(octets, (o) => o.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}
