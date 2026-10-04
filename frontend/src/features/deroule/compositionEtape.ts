// Les décisions du formulaire de composition d'une étape (E01US024) — logique pure, aucun React.
//
// Le formulaire détient l'état saisi ; ce module dit quelles fiches il offre, s'il peut soumettre,
// et quelle étape il envoie. DETTE-080 : `features/phases/Phases.tsx` porte un jumeau de ces règles.

import { TYPES_ARRETABLES, TYPES_EN_TABLEAU, type TypePhase } from '../../shared/phases/catalogue'
import { estValide as arretsValides, versArrets, type EtatArrets } from '../../shared/phases/arrets'
import {
  estValide as baremeDuelValide,
  TYPES_A_BAREME_DE_DUEL,
  versReglage as versReglageBaremeDuel,
  type EtatBaremeDuel,
} from '../../shared/phases/baremeDuel'
import {
  estValide as bsoValide,
  versReglage as versReglageBso,
  type EtatBigShootOff,
} from '../../shared/phases/bigShootOff'
import {
  estValide as collineValide,
  versReglage as versReglageColline,
  type EtatColline,
} from '../../shared/phases/colline'
import {
  estValide as decoupageValide,
  versDecoupage,
  type EtatDecoupage,
} from '../../shared/phases/decoupage'
import { versDureePrevue } from '../../shared/phases/horaires'
import {
  estValide as poulesValides,
  versReglage as versReglagePoules,
  type EtatPoules,
} from '../../shared/phases/poules'
import {
  estValide as profondeurValide,
  versProfondeur,
  type EtatProfondeur,
} from '../../shared/phases/profondeur'
import {
  estValide as suisseValide,
  versReglage as versReglageSuisse,
  type EtatSuisse,
} from '../../shared/phases/suisse'
import type { Etape, Source } from '../patrimoine/api'
import { lireEntier } from './sequence'

export interface SaisieEtape {
  type: TypePhase
  nbVolees: string
  nbFleches: string
  effectif: string
  sources: Source[]
  profondeur: EtatProfondeur
  poules: EtatPoules
  bigShootOff: EtatBigShootOff
  suisse: EtatSuisse
  colline: EtatColline
  baremeDuel: EtatBaremeDuel
  equipes: Etape['equipes']
  decoupage: EtatDecoupage
  arrets: EtatArrets
  titre: string
  duree: string
}

export interface FichesOffertes {
  enTableau: boolean
  estPoules: boolean
  estBigShootOff: boolean
  estSuisse: boolean
  estColline: boolean
  aBaremeDeDuel: boolean
  estEliminationDirecte: boolean
  estQualification: boolean
  arretable: boolean
}

export function fichesOffertes(type: TypePhase, decoupage: EtatDecoupage): FichesOffertes {
  return {
    enTableau: TYPES_EN_TABLEAU.includes(type),
    estPoules: type === 'poules',
    estBigShootOff: type === 'big_shoot_off',
    estSuisse: type === 'suisse',
    estColline: type === 'colline',
    aBaremeDeDuel: TYPES_A_BAREME_DE_DUEL.has(type),
    // Pas `aBaremeDeDuel` : poules, suisse et colline ont un barème mais pas d'équipes (ADR-0120).
    estEliminationDirecte: type === 'elimination_directe',
    // E05US035 : le découpage en tours n'existe que pour la qualification — c'est le seul format
    // dont le nombre de tours n'est pas déjà porté par sa structure.
    estQualification: type === 'qualification',
    arretable: estArretable(type, decoupage),
  }
}

// E05US033 : `TYPES_ARRETABLES` — les types qui annoncent leurs tours, donc les seuls où une
// pause puisse se poser. Même miroir et même raison que dans l'écran des phases. ⚠️ **Pour une
// qualification, l'arrêtabilité dépend du RÉGLAGE, pas du type** : non découpée, elle n'a qu'un
// tour, aucune frontière où poser une pause, et le `PUT` étant total la soumission entière
// échouerait. ⚠️ Ici le découpage est **en cours de saisie** : on lit l'état du formulaire, pas
// une phase persistée, pour que cocher « 2 tours » ouvre la fiche d'arrêts immédiatement.
// `versDecoupage` rend `null` pour un seul tour et `undefined` si illisible — les deux ferment.
function estArretable(type: TypePhase, decoupage: EtatDecoupage): boolean {
  return (
    TYPES_ARRETABLES.has(type) &&
    (type !== 'qualification' || (versDecoupage(decoupage) ?? null) !== null)
  )
}

// Un barème n'est porté que si **les deux** valeurs sont lisibles. Sinon `null` : c'est un
// **brouillon** de qualification, l'état que le CA rend explicitement licite. Un premier jet
// envoyait `Number('') === 0`, donc `0 volées` — refusé en 422 par `BaremeQualification`, si bien
// que « je remplirai le barème plus tard » était le seul brouillon naturel… et le seul impossible.
export function baremeSaisi(
  saisie: Pick<SaisieEtape, 'type' | 'nbVolees' | 'nbFleches'>,
): Etape['bareme'] {
  const volees = lireEntier(saisie.nbVolees)
  const fleches = lireEntier(saisie.nbFleches)
  return saisie.type === 'qualification' &&
    typeof volees === 'number' &&
    typeof fleches === 'number'
    ? { nb_volees: volees, nb_fleches_par_volee: fleches }
    : null
}

export function saisieInvalide(
  saisie: Pick<SaisieEtape, 'nbVolees' | 'nbFleches' | 'effectif'>,
): boolean {
  return (
    lireEntier(saisie.nbVolees) === undefined ||
    lireEntier(saisie.nbFleches) === undefined ||
    lireEntier(saisie.effectif) === undefined
  )
}

// Deux conditions de blocage, **un message chacune**. Les fondre ferait afficher au seuil vide le
// conseil générique « laissez le champ vide pour ne rien déclarer » — l'exact contraire de ce
// qu'il faut faire, puisqu'un top N sans rang d'arrêt est précisément ce qui est refusé.
export function soumissionBloquee(saisie: SaisieEtape): boolean {
  const fiches = fichesOffertes(saisie.type, saisie.decoupage)
  return (
    saisieInvalide(saisie) ||
    (fiches.enTableau && !profondeurValide(saisie.profondeur)) ||
    (fiches.estPoules && !poulesValides(saisie.poules)) ||
    (fiches.estBigShootOff && !bsoValide(saisie.bigShootOff)) ||
    (fiches.estSuisse && !suisseValide(saisie.suisse)) ||
    (fiches.estColline && !collineValide(saisie.colline)) ||
    (fiches.aBaremeDeDuel && !baremeDuelValide(saisie.baremeDuel)) ||
    (fiches.estQualification && !decoupageValide(saisie.decoupage)) ||
    // E05US033 : le contenu ne se juge que là où il est offert — une étape non arrêtable soumet
    // une liste vide, quoi qu'il reste dans l'état d'édition.
    !arretsValides(saisie.arrets)
  )
}

export function construireEtape(saisie: SaisieEtape, ordre: number): Etape {
  const fiches = fichesOffertes(saisie.type, saisie.decoupage)
  const bareme = baremeSaisi(saisie)
  return {
    ordre,
    type: saisie.type,
    // La qualification, et elle seule, porte barème et grain — c'est ce que le domaine exige, et
    // les proposer ailleurs offrirait un réglage que le serveur refuse (422).
    bareme,
    validation:
      saisie.type === 'qualification' && bareme !== null
        ? { type: 'fin_de_serie', n_volees: null }
        : null,
    sources: saisie.sources,
    effectif: lireEntier(saisie.effectif) ?? null,
    // Même garde que le barème : une profondeur n'a de sens que sur un tableau. Retyper une phase
    // de tableau en poule **efface** donc le réglage plutôt que de l'envoyer se faire refuser.
    profondeur: fiches.enTableau ? (versProfondeur(saisie.profondeur) ?? null) : null,
    // Même garde encore : un réglage de poules porté par une élimination directe serait refusé en
    // 422 (`ReglageDePoulesInvalide`). Retyper la phase l'**efface** donc, au lieu de l'envoyer se
    // faire recaler — symétrique exact de la ligne au-dessus.
    poules: fiches.estPoules ? (versReglagePoules(saisie.poules) ?? null) : null,
    // Même garde encore : un réglage de Big Shoot Off porté par un autre type serait refusé en 422
    // (`ConfigurationBigShootOffInvalide`). Retyper la phase l'**efface** donc. La garde compte
    // davantage ici qu'ailleurs : ce réglage décrit **qui sort**.
    big_shoot_off: fiches.estBigShootOff ? (versReglageBso(saisie.bigShootOff) ?? null) : null,
    // Même garde encore (E05US030) : un nombre de rondes porté par un autre type serait refusé en
    // 422. Retyper la phase l'**efface** donc, au lieu de l'envoyer se faire recaler.
    suisse: fiches.estSuisse ? (versReglageSuisse(saisie.suisse) ?? null) : null,
    // Même garde encore (E05US027) : un réglage de colline porté par un autre type serait refusé en
    // 422. Retyper l'étape l'**efface** donc, au lieu de l'envoyer se faire recaler.
    colline: fiches.estColline ? (versReglageColline(saisie.colline) ?? null) : null,
    bareme_duel: fiches.aBaremeDeDuel ? (versReglageBaremeDuel(saisie.baremeDuel) ?? null) : null,
    equipes: fiches.estEliminationDirecte ? saisie.equipes : null,
    // Même garde encore (E05US033) : un arrêt porté par un type qui n'annonce pas ses tours est
    // refusé en 422. Retyper l'étape l'**efface** donc, comme les quatre réglages ci-dessus.
    // Même garde encore (E05US035) : un découpage porté par un autre type serait refusé en 422.
    // Retyper l'étape l'**efface** donc, comme ses voisins.
    decoupage: fiches.estQualification ? (versDecoupage(saisie.decoupage) ?? null) : null,
    arrets: fiches.arretable ? (versArrets(saisie.arrets) ?? []) : [],
    // E16US002 — vidé = titre **retiré**. ⚠️ **Aucune garde de type ici**, à la différence des cinq
    // réglages ci-dessus : un titre n'appartient à aucun type, et « Tableau des jeunes » reste
    // juste si l'étape devient des poules. Le serveur ne le refuse sur aucun type.
    titre: saisie.titre.trim() === '' ? null : saisie.titre,
    duree_prevue: versDureePrevue(saisie.duree),
  }
}
