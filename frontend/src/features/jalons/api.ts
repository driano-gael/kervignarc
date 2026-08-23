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
  // À `false`, l'action passe **quand même** malgré `pret: false` (`D-15`). Ne sert jamais à
  // désactiver un bouton — cf. `PretA.tsx`.
  bloquant: boolean
}

export function getPreparationJalon(tournoiId: number, jalon: Jalon): Promise<PreparationJalon> {
  return fetchJson<PreparationJalon>(`/api/v1/tournois/${tournoiId}/jalons/${jalon}`)
}
