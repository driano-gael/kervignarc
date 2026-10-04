// Logique pure de la saisie en duels (E04US013) — libellés, avancement, injection optimiste.
//
// Isolée du rendu React pour être **testée** (vitest en node, sans DOM). Le serveur reste
// l'**autorité** (mode, barème, zones, **résultat** — ADR-0049 : le front ne recompute pas l'issue
// d'un duel) : ces fonctions ne pilotent que l'affichage — total provisoire d'une volée en frappe,
// quelle manche saisir, libellé du tour, et l'état **optimiste** d'un duel dont un acte est en file
// hors-ligne (pour que le scoreur continue au lieu de rester bloqué).

import type { FamilleDuel } from '../../shared/stores/fileDuelsHorsLigneStore'
import type {
  Barrage,
  Cote,
  Duel,
  Manche,
  ModeDuel,
  Phase,
  SaisirBarrage,
  SaisirManche,
} from './api'

// Points d'une valeur de zone : `M` (manqué) = 0, sinon la valeur. ⚠️ `DETTE-111` — **réécrit** la
// règle de `domain/blason.points_zone`, que la saisie de qualification, elle, lit servie par le
// barème (E17US011). Le duel n'a pas encore de table servie : c'est le site qui reste.
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

// Un duel tranché, ou à égalité en attente de son barrage (4-4 au club, E01US011), n'accepte plus de
// manche **neuve** : le serveur la refuse (`DuelDejaTranche`). Les manches saisies restent éditables.
export function mancheNeuveFermee(duel: Pick<Duel, 'resultat'>): boolean {
  return duel.resultat?.termine === true || duel.resultat?.barrage_requis === true
}

// La prochaine manche à saisir : la **plus petite** (1..nbManches) pas encore saisie ; si toutes le
// sont, ou si aucune manche neuve n'est plus permise, on reste sur la **dernière saisie**.
// Jumeau de `volees.prochaineASaisir`.
export function prochaineMancheASaisir(
  duel: Pick<Duel, 'manches' | 'resultat'>,
  nbManches: number,
): number {
  if (mancheNeuveFermee(duel) && duel.manches.length > 0) {
    return Math.max(...duel.manches.map((m) => m.numero))
  }
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

// Un bye ou un duel sans adversaires connus est affiché dans la liste, mais non ouvrable.
export function estOuvrable(statut: StatutDuel): boolean {
  return statut !== 'bye' && statut !== 'attente_adversaires'
}

// La saisie en duels ne vaut que pour une phase de **tableau** : on ne propose que celles-là (le
// serveur reste l'autorité — `phase_pas_un_tableau` si l'on force — mais restreindre évite d'y
// arriver par mégarde). Jumeau du sélecteur du plan de duels (E03US009).
export function phasesDeTableau(phases: readonly Phase[]): Phase[] {
  return phases.filter((p) => p.type === 'elimination_directe')
}

// Changer de créneau rend l'ancien `phaseId` étranger à la liste : le garder ferait scorer le
// tableau de l'autre départ, avec un identifiant valide et donc sans la moindre erreur.
export function retenirPhase(phaseId: number | null, tableaux: readonly Phase[]): number | null {
  return phaseId !== null && tableaux.some((phase) => phase.id === phaseId) ? phaseId : null
}

// Verrou : duel validé (autorité serveur) OU **validation en file hors-ligne** — dans ce dernier cas
// on ferme la saisie **localement**, comme le ferait le serveur en ligne (`DuelVerrouille`). Sans ce
// verrou optimiste, le scoreur pourrait rééditer une manche APRÈS avoir validé hors-ligne : au rejeu
// FIFO, la validation scellerait le résultat d'avant correction, et la manche corrigée rebondirait en
// 422 (perte silencieuse). Se réconcilie à la relecture serveur post-rejeu (revue adversariale).
export function saisieVerrouillee(
  duel: Pick<Duel, 'validee_par' | 'validation_en_attente'>,
): boolean {
  return duel.validee_par !== null || duel.validation_en_attente === true
}

// Les deux archers à qui proposer le forfait, ou `null` s'il n'y a pas de bouton à rendre :
// uniquement dans un tableau (ni poule — ADR-0083 §7 —, ni suisse, ni colline), jamais sur une
// saisie close.
// DETTE-120 : un forfait se déclare pour un archer — rien à proposer à un duel d'équipes.
export function duellistesDuForfait(
  duel: Pick<Duel, 'haut' | 'bas' | 'validee_par' | 'validation_en_attente'>,
  famille: FamilleDuel,
): { hautId: number; basId: number } | null {
  if (famille !== 'tableau' || saisieVerrouillee(duel)) return null
  const hautId = duel.haut?.archer_id
  const basId = duel.bas?.archer_id
  if (hautId == null || basId == null) return null
  return { hautId, basId }
}

// Les archers à router après validation (E04US018) — mais **seulement si la validation est
// partie**. Hors-ligne elle est mise en file (`validation_en_attente`) : le tableau n'a pas avancé
// côté serveur, le panneau annoncerait alors le duel qu'on vient de scorer comme « prochain ». On ne
// route pas sur une avancée qui n'a pas eu lieu. Un camp d'équipe n'a pas d'`archer_id`.
export function archersARouter(
  duel: Pick<Duel, 'haut' | 'bas'>,
  duelValide: Pick<Duel, 'validation_en_attente'>,
): number[] {
  if (duelValide.validation_en_attente === true) return []
  return [duel.haut?.archer_id, duel.bas?.archer_id].filter(
    (id): id is number => id !== undefined && id !== null,
  )
}

// Une pastille par manche du barème : saisie = pleine, visée = surlignée ; une manche non saisie
// est fermée dès qu'aucune manche neuve n'est plus permise.
export function pastillesManches(
  duel: Pick<Duel, 'manches' | 'resultat'>,
  nbManches: number,
  numeroActif: number,
): { numero: number; saisie: boolean; fermee: boolean; active: boolean; classes: string }[] {
  return Array.from({ length: nbManches }, (_, i) => {
    const numero = i + 1
    const saisie = duel.manches.some((m) => m.numero === numero)
    const active = numero === numeroActif
    // Jumeau de `saisie/pave.ts` `classesPastille` (sans la variante `--verrou`) — cf. E00US023.
    const classes = [
      'saisie__nav-volee',
      saisie ? 'saisie__nav-volee--saisie' : '',
      active ? 'saisie__nav-volee--actif' : '',
    ]
      .filter((c) => c !== '')
      .join(' ')
    return { numero, saisie, fermee: !saisie && mancheNeuveFermee(duel), active, classes }
  })
}

// Barème de saisie d'un duel : le serveur peut ne pas le porter (duel pas encore réglé) ; l'écran
// retombe alors sur une manche de trois flèches.
export function baremeDeManche(duel: Pick<Duel, 'nb_manches' | 'nb_fleches_par_volee'>): {
  nbManches: number
  nbFleches: number
} {
  return { nbManches: duel.nb_manches ?? 1, nbFleches: duel.nb_fleches_par_volee ?? 3 }
}

// Les gestes ouverts sur une manche en frappe. On n'enregistre que les **deux** camps complets ;
// le camp actif plein ferme les zones, et un envoi en cours fige tout.
export function etatManche(manche: {
  bufferHaut: readonly string[]
  bufferBas: readonly string[]
  campActif: Cote
  nbFleches: number
  envoiEnCours: boolean
}): { campComplet: boolean; zonesActives: boolean; effacable: boolean; enregistrable: boolean } {
  const { bufferHaut, bufferBas, campActif, nbFleches, envoiEnCours } = manche
  const buffer = campActif === 'haut' ? bufferHaut : bufferBas
  const campComplet = buffer.length >= nbFleches
  const deuxComplets = bufferHaut.length >= nbFleches && bufferBas.length >= nbFleches
  return {
    campComplet,
    zonesActives: !campComplet && !envoiEnCours,
    effacable: buffer.length > 0 && !envoiEnCours,
    enregistrable: deuxComplets && !envoiEnCours,
  }
}

// Le camp actif après une flèche : camp rempli, on bascule automatiquement sur l'autre s'il reste à
// saisir (fluidité tactile).
export function campApresFleche(
  campActif: Cote,
  nbFlechesActif: number,
  nbFlechesAutre: number,
  nbFleches: number,
): Cote {
  if (nbFlechesActif >= nbFleches && nbFlechesAutre < nbFleches) {
    return campActif === 'haut' ? 'bas' : 'haut'
  }
  return campActif
}

// Empreinte du contenu **persisté** d'une manche : quand elle change, les tampons du pavé y sont
// remis (ajustement d'état au rendu, cf. `SaisieManche`).
export function signatureManche(numero: number, existante: Manche | null): string {
  return `${numero}:${(existante?.haut ?? []).join(',')}:${(existante?.bas ?? []).join(',')}`
}

// Empreinte du barrage **serveur** : quand elle change (rejeu, relecture), le formulaire s'y resynchronise.
export function signatureBarrage(barrage: Barrage | null): string {
  return `${(barrage?.haut ?? []).join(',')}:${(barrage?.bas ?? []).join(',')}:${barrage?.gagnant_designe ?? ''}`
}

// La désignation n'est requise (et proposée) que si les deux camps sont complets **et à égalité
// de total** — la règle du serveur (§8.2, E13US003).
export function etatBarrage(
  flechesHaut: readonly string[],
  flechesBas: readonly string[],
  designe: Cote | null,
  nbFleches: number,
): { complets: boolean; egales: boolean; pretAEnvoyer: boolean } {
  const complets = flechesHaut.length === nbFleches && flechesBas.length === nbFleches
  // DETTE-111 — `totalVolee` recopie la règle zone → points du serveur, et décide ici de la désignation.
  const egales = complets && totalVolee(flechesHaut) === totalVolee(flechesBas)
  return { complets, egales, pretAEnvoyer: complets && (!egales || designe !== null) }
}

// À une flèche de barrage, toucher une zone la **remplace** (sélection unique) ; à plusieurs
// (équipe, E13US003), les flèches s'ajoutent.
export function flechesApresZone(
  valeurs: readonly string[],
  zone: string,
  nbFleches: number,
): string[] {
  return nbFleches === 1 ? [zone] : [...valeurs, zone]
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
      haut: corps.fleches_haut,
      bas: corps.fleches_bas,
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
