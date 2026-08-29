// Accès API des **jalons « prêt à… »** (E16US012). Miroir des DTO de `api/v1/jalons.py`.
// Route **admin** (portée `'admin'` par défaut de `fetchJson`, en-tête `Authorization: Bearer`).
//
// Une **route unique paramétrée** par le membre, image de la forme unique décidée au domaine
// (ADR-0096) : quatre fonctions d'accès jumelles auraient rouvert côté front la divergence que
// l'US ferme.

import { fetchJson } from '../../shared/api/client'
import type { LigneCompletude } from '../completude/api'

// Les quatre membres de la famille (miroir de `domain.jalon.Jalon`). `archiver` et `exporter`
// existent dans le type mais n'ont **pas encore d'écran** : le serveur répond 404
// (`jalon_non_instruit`) plutôt qu'une liste vide qui se lirait « rien ne manque, allez-y ».
export type Jalon = 'demarrer' | 'terminer' | 'archiver' | 'exporter'

export interface PreparationJalon {
  jalon: Jalon
  // « Prêt à démarrer ? » — **dérivée du jalon côté serveur** : le front ne tient pas sa propre
  // table de libellés, qui divergerait au premier membre ajouté.
  question: string
  lignes: LigneCompletude[]
  // La réponse binaire : l'action passera-t-elle ?
  pret: boolean
  // La question a-t-elle encore un objet depuis le statut courant ? À `false`, l'écran ne rend pas
  // de verdict — seulement la raison. ⚠️ **Ne pas le déduire de `lignes`** : le membre *terminer*
  // rend sa liste à tout statut, c'est ce champ qui porte l'information.
  question_posee: boolean
  // À `false`, l'action passe **quand même** malgré `pret: false` (`D-15`). Ne sert jamais à
  // désactiver un bouton — cf. `PretA.tsx`.
  bloquant: boolean
  // La **cause chiffrée** du blocage (« 8 archer(s) inscrit(s) sur le départ 2 pour 34 requis… »),
  // `null` s'il n'y en a pas. C'est la phrase du refus serveur lui-même : l'avertissement d'avant
  // le clic et le 409 d'après ne peuvent pas énoncer deux causes différentes.
  detail: string | null
  // **Quand** ce refus tombera (« au démarrage », « dès le passage en « prêt » »), `null` s'il n'y
  // a rien à refuser. Dérivé côté serveur de la garde qui bloque en premier : les deux gardes de
  // *démarrer* ne tombent pas au même clic, et l'écran ne doit pas le deviner.
  moment: string | null
}

export function getPreparationJalon(tournoiId: number, jalon: Jalon): Promise<PreparationJalon> {
  return fetchJson<PreparationJalon>(`/api/v1/tournois/${tournoiId}/jalons/${jalon}`)
}

// --- Aperçu de liste (E16US010) ------------------------------------------------------------

// Les deux niveaux de pastille du CA, plus l'absence de pastille. Miroir de
// `domain.jalon.NiveauPreparation`.
export type NiveauPreparation = 'aucun' | 'avertissement' | 'alerte'

export interface ApercuJalon {
  tournoi_id: number
  niveau: NiveauPreparation
  // Ce que la pastille dit au survol — `null` exactement quand le niveau est `aucun`. C'est la
  // phrase du refus serveur quand il y en a une : l'aperçu et l'écran du jalon ne peuvent pas
  // énoncer deux causes différentes du même manque.
  resume: string | null
}

// ⚠️ **Une requête pour toute la liste.** La complétude est par ailleurs une lecture par tournoi ;
// la faire depuis le front tournoi par tournoi partait en N requêtes.
// ⚠️ L'adresse est **hors** de `/api/v1/tournois` : sous ce préfixe, `jalons` était appariable
// comme identifiant de tournoi (cf. `api/v1/jalons.py`). Ne pas l'y ramener.
export function getApercusJalon(jalon: Jalon): Promise<ApercuJalon[]> {
  return fetchJson<ApercuJalon[]>(`/api/v1/jalons/${jalon}/apercus`)
}
