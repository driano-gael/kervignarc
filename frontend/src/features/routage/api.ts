// Accès API du panneau de routage (E04US018). Miroir des DTO de `api/v1/routage.py`.
//
// Portée `'aucune'` : c'est une **lecture publique** (contrat E10US001), et surtout la même donnée
// que liront les trois autres canaux de routage (`D-09` — appli publique E07US008, écran de salle
// E07US004). Le panneau s'affiche donc aussi bien sur la tablette (jeton de poste) que sur l'écran
// scoreur (jeton de scoreur), sans dépendre de l'identité qui le consulte.

import { fetchJson } from '../../shared/api/client'

export interface Duelliste {
  archer_id: number
  nom: string
  prenom: string
}

// Le prochain rendez-vous d'un archer. `cible`/`position` sont `null` au-delà du 1er tour (le
// placement intégral 1→N est E05US010) et `manque` dit alors pourquoi — on **nomme** l'attente
// plutôt que de laisser un blanc. `adversaire` est `null` tant que le duel amont n'est pas tranché,
// `sources_en_attente` en donnant alors le numéro.
export interface ProchainDuel {
  numero: number
  tour: number
  libelle: string
  cible: number | null
  position: string | null
  adversaire: Duelliste | null
  sources_en_attente: number[]
  manque: string | null
  // L'inverse de `manque` : la cible **est** là, mais le duel n'est pas côte à côte (plan matérialisé
  // sur un autre appariement, ou cibles trop petites). On affiche la cible **et** l'avertissement —
  // retirer une information juste ne rend service à personne.
  alerte: string | null
}

export type IssueRoutage =
  | 'prochain_duel'
  | 'prochaine_manche'
  | 'termine'
  | 'repeche'
  // E05US030 : il est dans la phase, en course, mais **rien à tirer maintenant** — le porteur du
  // bye d'une ronde impaire, ou celui dont la rencontre vient d'être validée pendant que la ronde
  // s'achève. `E05US026` servait ce cas sous `indisponible` avec un motif, faute de pouvoir toucher
  // au contrat d'API depuis une US backend seule : c'est un **rétrécissement** d'`indisponible`, pas
  // seulement un ajout.
  | 'en_attente'
  | 'indisponible'

// Le prochain rendez-vous d'un finaliste de **Big Shoot Off** (E05US028) — jamais un duel : un Big
// Shoot Off n'oppose personne, tous les finalistes sont sur la ligne et c'est le classement de la
// manche qui élimine. `elimine` dit combien sortiront à l'issue de ce tour, ce qui compte davantage
// pour le tireur que le numéro de la manche.
//
// ⚠️ `cible`/`position` sont **toujours `null` aujourd'hui** et `manque` le dit en clair : le
// routage ne lit pas le plan du créneau pour cette phase (`DETTE-059`). On affiche le manque plutôt
// que de laisser un blanc, qui se lirait comme une panne réseau (`P-3`).
export interface ProchaineManche {
  numero: number
  elimine: number
  cible: number | null
  position: string | null
  manque: string | null
}

// La phase qui **reprend** un repêché (E07US008). Elle n'est pas dans son tableau : un repêché en
// sort, et c'est une phase avale qui le prélève. Pas de libellé tout fait côté serveur — le front
// sait déjà nommer un type de phase (`LIBELLE_TYPE`), et le dupliquer le ferait diverger.
export interface DestinationRepechage {
  phase_id: number
  ordre: number
  type: string
}

export interface RoutageArcher {
  archer_id: number
  nom: string
  prenom: string
  issue: IssueRoutage
  prochain: ProchainDuel | null
  // **Exclusif de `prochain`** : un archer n'a jamais les deux, et son issue dit lequel lire.
  prochaine_manche: ProchaineManche | null
  // `rang_final` = le rang **exact**, décerné par un match terminal. `rang_min`/`rang_max` = la
  // **fourchette acquise**, qui vaut aussi dans un tableau tronqué au podium : le battu d'un quart
  // est 5ᵉ-8ᵉ *ex æquo*, et aucun match n'a été joué pour les départager. Quand le rang exact
  // existe, la fourchette s'y referme — c'est la même notion à deux profondeurs.
  rang_final: number | null
  rang_min: number | null
  rang_max: number | null
  tour_sortie: string | null
  destination: DestinationRepechage | null
  motif: string | null
}

export interface Routage {
  // `null` = **aucune phase d'élimination configurée**, à distinguer d'une liste d'archers vide
  // (« le tableau ne route personne »). Sans ça, un écran de salle afficherait un pas de tir désert
  // au lieu de dire qu'on n'en est pas là.
  phase_id: number | null
  archers: RoutageArcher[]
}

// ⚠️ **L'entrée est le créneau** (E01US025, ADR-0075) : « le tableau qui vient » n'a de sens que
// dans une séquence, et un tournoi en a autant qu'il a de départs. À la maille tournoi, le serveur
// renvoyait tout le monde vers le tableau du **premier** créneau — les archers de l'après-midi
// compris, sur les quatre canaux à la fois. `phaseId` omis = le serveur vise la première
// élimination directe non terminée **du créneau**. L'ordre des `archerIds` est **conservé** par le
// serveur.
export function getRoutage(
  departId: number,
  archerIds: number[],
  phaseId?: number | null,
): Promise<Routage> {
  const parametres = new URLSearchParams()
  for (const archerId of archerIds) parametres.append('archer_id', String(archerId))
  if (phaseId != null) parametres.set('phase_id', String(phaseId))
  return fetchJson<Routage>(
    `/api/v1/routage/departs/${departId}?${parametres}`,
    undefined,
    'aucune',
  )
}

// **Toutes** les affectations du tableau, dans l'ordre du pas de tir (E07US008) — aucun `archer_id`
// à fournir. C'est ce qui distingue cette lecture de `getRoutage` : l'écran de salle et la table de
// l'organisation ne connaissent pas la liste des archers, et la leur faire reconstituer reviendrait
// à leur faire connaître le tableau. Même type de réponse : les quatre canaux disent la même chose.
export function getAffectations(departId: number, phaseId?: number | null): Promise<Routage> {
  const parametres = new URLSearchParams()
  if (phaseId != null) parametres.set('phase_id', String(phaseId))
  return fetchJson<Routage>(
    `/api/v1/routage/departs/${departId}/affectations?${parametres}`,
    undefined,
    'aucune',
  )
}
