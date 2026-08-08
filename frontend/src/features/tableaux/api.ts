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
// ⚠️ `place_en_jeu` n'est renseigné que sur les matchs **terminaux** (ceux qui départagent deux
// rangs) : il vaut `[1, 2]` pour la finale, `[5, 6]` pour le match de la 5ᵉ place, et **`null`
// partout ailleurs** — y compris sur un match des places 5-8 disputé au tour d'une demi-finale.
// C'est `plage` qui distingue ces branches-là, et `libelle` qui les nomme.
//
// `termine` et `validee` ne disent pas la même chose et l'écart est **visible à l'écran** : le tir
// est allé au bout (`termine`) mais le scoreur n'a pas encore scellé (`validee`), donc l'arbre
// n'avance pas. C'est le même vocabulaire « en attente de validation » / « validé » qu'E07US009.
export interface DuelPublic {
  numero: number
  tour: number
  // Le nom du match — « Demi-finale », « Petite finale », « Places 5 à 8 », « Match pour la 5ᵉ
  // place » —, calculé par le **domaine** (`domain/tableau.py::libelle_tour`). Ne pas le
  // recalculer ici : c'est du vocabulaire métier (règle 3), il n'a qu'un domicile, et un premier
  // jet de cette US a prouvé le coût de l'oublier (« Demi-finales » affiché sur un match des
  // places 5-8). `DETTE-020` en compte déjà deux, n'en ouvrons pas un troisième.
  libelle: string
  place_en_jeu: number[] | null
  // La **branche** du match : `[1, 8]` pour le tableau principal, `[5, 8]` pour le sous-tableau de
  // placement qui en descend. Contrairement à `place_en_jeu`, elle existe **dès le premier tour** —
  // c'est elle qui permet de distinguer deux branches disputées au même tour.
  plage: number[] | null
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
  // ⚠️ **Non nul = cette phase n'a pas encore d'arbre** (E05US024, ADR-0081) : elle prélève des
  // places que sa phase source n'a pas encore attribuées — typiquement une consolante « les rangs 5
  // à 8 du tableau » composée le matin, quarts non tirés. Porte l'`ordre` de la phase attendue.
  //
  // Avant cette US, le serveur montait quand même un arbre, en départageant les archers encore en
  // lice sur leur rang de qualification : la consolante affichait les 4 derniers **qualifiés** au
  // lieu des 4 battus des quarts. Bien formé, plausible, et faux. Les champs de dimensions valent
  // 0 et les listes sont vides quand ce champ est renseigné.
  en_attente_de: number | null
}

export interface Tableaux {
  // ⚠️ **Les arbres sont ceux d'un créneau** (E01US025, ADR-0075) : deux départs portent chacun
  // leur tableau du même rang, et rien dans `TableauPublic` ne les distinguerait. À la maille
  // tournoi, la réponse les concaténait — l'écran montrait l'arbre du matin sous l'onglet de
  // l'après-midi.
  depart_id: number
  tableaux: TableauPublic[]
}

export function getTableaux(departId: number): Promise<Tableaux> {
  return fetchJson<Tableaux>(`/api/v1/tableaux/departs/${departId}`)
}
