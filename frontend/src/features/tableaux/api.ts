// Accès API de la vue publique des tableaux (E07US005) — « voir les arbres en direct ».
//
// Miroir du DTO **public restreint** exposé par `backend/api/v1/tableaux.py`. Il est volontairement
// plus pauvre que celui du scoreur (`saisie-duels`) : ni manches, ni barrage, ni zones, ni identité
// du valideur (règle 6). Ne pas « compléter » ces types en recopiant ceux de la saisie — l'absence
// de ces champs **est** la décision, et le test `test_le_dto_public_ne_porte_ni_identite_de_scoreur…`
// la verrouille côté serveur.

import { fetchJson } from '../../shared/api/client'

// Un duelliste tel que l'arbre l'affiche. `archer_id` sert à reconnaître un **archer suivi**
// (E07US006) sans comparer des noms — comparaison qui casse au premier homonyme, et il y en a.
export interface DuellistePublic {
  archer_id: number
  nom: string
  prenom: string
}

// Un match de l'arbre.
//
// `place_en_jeu` nomme l'enjeu sans le déduire du tour : `[1, 2]` c'est la finale, `[5, 8]` un
// match de placement. La déduction par le numéro de tour serait fausse dès qu'un tableau descend
// sous le podium (E06US006), ce qui est désormais un réglage courant.
//
// `termine` et `validee` ne disent pas la même chose et l'écart est **visible à l'écran** : le tir
// est allé au bout (`termine`) mais le scoreur n'a pas encore scellé (`validee`), donc l'arbre
// n'avance pas. C'est le même vocabulaire « en attente de validation » / « validé » qu'E07US009.
export interface DuelPublic {
  numero: number
  tour: number
  place_en_jeu: number[] | null
  haut: DuellistePublic | null
  bas: DuellistePublic | null
  est_bye: boolean
  points_haut: number | null
  points_bas: number | null
  vainqueur: 'haut' | 'bas' | null
  termine: boolean
  validee: boolean
}

export interface PlacePodium {
  rang: number
  duelliste: DuellistePublic
}

// Un arbre du tournoi. `type` est une chaîne de `TypePhase` — le libellé se prend dans
// `shared/phases/catalogue.ts` (`libelleType`), qui est son domicile unique (règle 3).
export interface TableauPublic {
  phase_id: number
  ordre: number
  type: string
  effectif: number
  taille: number
  nb_tours: number
  est_termine: boolean
  duels: DuelPublic[]
  podium: PlacePodium[]
}

export interface Tableaux {
  tournoi_id: number
  tableaux: TableauPublic[]
}

export function getTableaux(tournoiId: number): Promise<Tableaux> {
  return fetchJson<Tableaux>(`/api/v1/tableaux/${tournoiId}`)
}
