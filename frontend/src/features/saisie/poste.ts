// Décisions de l'écran du poste de cible (E04US002) — logique **pure**, testée sans rendu (E00US024).
//
// Qui est l'archer actif, qui signe, quel état de l'écran montrer, quand la cible est close : ce que
// `Saisie` décidait dans son corps, ici où vitest (environnement node) peut le vérifier.

import { ErreurApi } from '../../shared/api/client'
import { serieClose } from '../routage/presentation'
import type { LigneGrille, Volee } from './api'

// Ce qui est ouvert pour un archer : la volée choisie (`null` = sa prochaine à saisir) et la flèche
// que la prochaine frappe remplace (`null` = à la suite). Portée par `Saisie`, lue par la ligne de
// l'archer actif et par le pavé — une seule source, pour qu'ils ne divergent pas.
export interface Ouverture {
  archerId: number
  numero: number | null
  fleche: number | null
}

export interface AffichagePoste {
  // Départ courant non fixé : le serveur refuse la grille (409, ADR-0034 §1). C'est un état attendu,
  // pas un incident — on invite à choisir un départ plutôt que d'afficher une erreur.
  besoinDepart: boolean
  // L'état « Rattaché » de S01 : la tablette sait quelle cible elle sert, le tir n'a rien à montrer
  // encore. Exclut le chargement et l'erreur dure, où un numéro géant n'aurait aucun sens.
  confirmation: boolean
  selecteurDepart: boolean
  messageErreur: boolean
  grilleVide: boolean
  travail: boolean
}

export function affichagePoste(grille: {
  enErreur: boolean
  erreur: unknown
  succes: boolean
  nbLignes: number
}): AffichagePoste {
  const besoinDepart =
    grille.enErreur &&
    grille.erreur instanceof ErreurApi &&
    grille.erreur.code === 'depart_courant_non_defini'
  return {
    besoinDepart,
    confirmation: (besoinDepart || grille.succes) && grille.nbLignes === 0,
    selecteurDepart: besoinDepart || grille.succes,
    messageErreur: grille.enErreur && !besoinDepart,
    grilleVide: grille.succes && grille.nbLignes === 0,
    travail: grille.succes && grille.nbLignes > 0,
  }
}

// **Le pavé est appelé, pas permanent** (retour maquettes S02, 04/08/2026). ⚠️ L'archer actif n'a
// donc **plus de repli** : un choix devenu obsolète referme le pavé au lieu de glisser
// silencieusement sur un autre archer — le vrai danger du repli (un tap malheureux saisissait pour A).
export function archerActifParmi(
  lignes: readonly LigneGrille[],
  archerChoisi: number | null,
): number | null {
  return archerChoisi !== null && lignes.some((l) => l.archer_id === archerChoisi)
    ? archerChoisi
    : null
}

// Le marqueur, lui, **garde** son repli sur le premier archer : c'est une signature, pas une cible
// de frappe. Sans nom par défaut, la première volée de la journée partirait avec `saisie_par: null`.
export function marqueurActifParmi(
  lignes: readonly LigneGrille[],
  marqueur: string | null,
): string | null {
  return marqueur !== null && lignes.some((l) => l.nom === marqueur)
    ? marqueur
    : (lignes[0]?.nom ?? null)
}

// ⚠️ **L'ouverture n'appartient qu'à l'archer actif** : dès qu'il change — autre nom touché, archer
// sorti de la grille (autre départ) — elle retombe, sans quoi une visée ressusciterait au retour et
// la frappe suivante remplacerait une flèche.
export function ouvertureDeLArcher(
  ouverture: Ouverture | null,
  archerActif: number | null,
): Ouverture | null {
  return ouverture !== null && ouverture.archerId === archerActif ? ouverture : null
}

// « Close » (E04US018) = toutes les volées du barème saisies **et** verrouillées par le scoreur —
// **ou** l'archer est forfait (E04US015 : sans cette clause, une seule DSQ priverait toute la cible
// du panneau de routage). `voleesParLigne[i]` : la série de `lignes[i]`, `undefined` si pas lue.
export function cibleClose(
  lignes: readonly LigneGrille[],
  voleesParLigne: readonly (Volee[] | undefined)[],
  nbVolees: number | null,
): boolean {
  return (
    lignes.length > 0 &&
    lignes.every((ligne, i) => serieClose(voleesParLigne[i] ?? [], nbVolees, ligne.forfait))
  )
}

// La **composition** de la grille, indifférente à l'ordre : c'est elle, pas un réordonnancement, qui
// réarme la bascule automatique du panneau de routage.
export function signatureComposition(archerIds: readonly number[]): string {
  return [...archerIds].sort((a, b) => a - b).join(',')
}
