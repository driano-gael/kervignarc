// Accès API de la feature « departs » (E02US004, ADR-0017) : CRUD des départs (créneaux) d'un
// tournoi. Miroir des DTO exposés par `api/v1/departs.py`. Routes **imbriquées sous le tournoi**
// (un départ n'existe pas hors de lui) : l'édition et la suppression portent donc le `tournoiId`.

import { fetchJson } from '../../shared/api/client'

// État de cycle de vie d'un créneau (E12US008), **dérivé** côté serveur (jamais stocké) :
// - `ouvert` : aucun score encore consigné → librement éditable ;
// - `lance` : une session de tir est en cours (au moins une flèche) ;
// - `clos` : toutes les séries du créneau sont closes.
// Éditer ou supprimer un créneau non `ouvert` demande une confirmation (409
// `depart_en_cours_non_confirme`, levé par `confirmeCycle`).
export type EtatDepart = 'ouvert' | 'lance' | 'clos'

export interface Depart {
  id: number
  tournoi_id: number
  numero: number
  // Horaire du créneau au format `HH:MM` (24 h), **obligatoire** (E02US010). Une vraie donnée
  // temporelle, plus un libellé libre : le serveur en refuse toute autre forme (422).
  horaire: string
  // Prix du créneau, en **centimes entiers** (ADR-0012) — l'unité est dans le nom. Obligatoire ;
  // `0` = gratuit. Voir `../competition/format` pour la mise en forme.
  tarif_centimes: number
  // Nombre maximal d'inscrits du créneau (E02US006), **facultatif** : `null` = pas de plafond. Une
  // inscription au-delà est refusée par le serveur (409 `depart_complet`).
  quota: number | null
  // État de cycle de vie dérivé (E12US008) : sert de badge et prévient qu'une édition/suppression
  // d'un créneau non `ouvert` sera signalée (confirmable).
  etat: EtatDepart
}

export interface NouveauDepart {
  tarif_centimes: number
  // Horaire `HH:MM` **obligatoire** (E02US010) : le front n'envoie que du `HH:MM` (masque + garde
  // d'envoi), le serveur reste l'autorité (422 si le format ne convient pas).
  horaire: string
  // Omis ou `null` = créneau sans plafond. L'édition est un **remplacement complet** : renvoyer le
  // quota courant pour le conserver (sinon il est retiré côté serveur).
  quota?: number | null
}

// L'édition porte sur les mêmes champs que la création (le numéro est fixe, attribué par le serveur).
export type ModifierDepart = NouveauDepart

export function getDeparts(tournoiId: number): Promise<Depart[]> {
  return fetchJson<Depart[]>(`/api/v1/tournois/${tournoiId}/departs`)
}

export function creerDepart(tournoiId: number, entree: NouveauDepart): Promise<Depart> {
  return fetchJson<Depart>(`/api/v1/tournois/${tournoiId}/departs`, {
    method: 'POST',
    body: JSON.stringify(entree),
  })
}

// `confirmeCycle` : confirmation de l'admin après un signalement `depart_en_cours_non_confirme`
// (409, E12US008) — le créneau est *lancé* ou *clos* (une session de tir a eu lieu). En **paramètre
// de requête** (le corps porte déjà les valeurs éditées), comme la suppression.
export function modifierDepart(
  tournoiId: number,
  departId: number,
  entree: ModifierDepart,
  confirmeCycle = false,
): Promise<Depart> {
  const parametres = confirmeCycle ? '?confirme_cycle=true' : ''
  return fetchJson<Depart>(`/api/v1/tournois/${tournoiId}/departs/${departId}${parametres}`, {
    method: 'PUT',
    body: JSON.stringify(entree),
  })
}

// Deux confirmations possibles, selon l'état du créneau (chacune en **paramètre de requête**, un
// DELETE n'ayant pas de corps — comme la suppression d'archer) :
// - `confirmeCycle` : lève le signalement `depart_en_cours_non_confirme` (409, E12US008) d'un
//   créneau *lancé*/*clos*. Il **subsume** la confirmation d'inscriptions côté serveur (un créneau
//   lancé porte forcément des inscriptions) — inutile d'envoyer les deux.
// - `autoriserSuppressionInscrits` : lève `depart_avec_inscriptions` (409, ADR-0018) d'un créneau
//   *ouvert* à inscriptions ; efface les inscriptions (payées à rembourser — E08US005). DETTE-007 :
//   confirmation **aveugle** (ne rappelle pas au serveur le décompte annoncé).
export function supprimerDepart(
  tournoiId: number,
  departId: number,
  autoriserSuppressionInscrits = false,
  confirmeCycle = false,
): Promise<void> {
  const parametres = new URLSearchParams()
  if (autoriserSuppressionInscrits) parametres.set('autoriser_suppression_inscrits', 'true')
  if (confirmeCycle) parametres.set('confirme_cycle', 'true')
  const suffixe = parametres.toString() ? `?${parametres.toString()}` : ''
  return fetchJson<void>(`/api/v1/tournois/${tournoiId}/departs/${departId}${suffixe}`, {
    method: 'DELETE',
  })
}
