// Logique pure de la saisie (E04US002) — points, volée à saisir, libellé de grain.
//
// Isolée du rendu React pour être **testée** (vitest tourne en environnement node, sans DOM). Le
// serveur reste l'**autorité** (barème, zones, cumul officiel) : ces fonctions ne servent qu'à
// piloter l'affichage — total provisoire d'une volée en cours, quelle volée saisir, etc.

import type { Grain, SaisirVolee, Serie, Volee } from './api'

// Ce que vaut une zone, **lu** dans la table que sert le barème (`points_par_zone`, domicile unique
// `domain/blason.points_zone` — E17US011). On sert la **règle**, pas un total : le poste valorise
// hors ligne des volées que le serveur n'a jamais reçues. Une valeur absente de la table → 0.
export type PointsParZone = Readonly<Record<string, number>>

export function pointsZone(valeur: string, table: PointsParZone): number {
  return table[valeur] ?? 0
}

// Total provisoire d'une volée en cours de frappe (avant enregistrement). Le cumul **officiel** de
// la série vient du serveur (volées validées uniquement) ; ceci n'est qu'un retour visuel immédiat.
// ⚠️ Depuis E17US008, **aucun écran de saisie n'affiche plus `Serie.cumul`** : la grille et le pavé
// montrent `cumulSaisi`. Le champ reste rendu par l'API et lu par la surface **scoreur**, qui le
// libelle « Total validé ». Ne pas conclure de sa présence que la cible voit le score officiel.
export function totalVolee(valeurs: readonly string[], table: PointsParZone): number {
  return valeurs.reduce((somme, valeur) => somme + pointsZone(valeur, table), 0)
}

// La flèche que désigne un tap sur une case de la ligne d'archer (E17US011, S02). Une case vide ne
// se vise pas : la volée se remplit dans l'ordre, un trou ne serait ni enregistrable ni lisible.
export function flecheVisee(caseTouchee: number, buffer: readonly string[]): number | null {
  return caseTouchee < buffer.length ? caseTouchee : null
}

// Une frappe du pavé : **remplace** la flèche visée, sinon s'ajoute à la suite. `null` = refusée
// (volée complète et rien de visé) — c'est ce qui laisse corriger une volée pleine avant envoi.
export function frapper(
  buffer: readonly string[],
  valeur: string,
  visee: number | null,
  nbFleches: number,
): string[] | null {
  if (visee !== null && visee < buffer.length) {
    return buffer.map((actuelle, i) => (i === visee ? valeur : actuelle))
  }
  return buffer.length < nbFleches ? [...buffer, valeur] : null
}

// Cumul **saisi** de la série : toutes les volées entrées, validées ou non.
//
// ⚠️ Ce n'est **pas** `Serie.cumul`, et l'écart est voulu des deux côtés. Le serveur ne somme que
// les volées **validées** — c'est le score officiel, celui que le départage du classement compte
// (`domain/serie.py`). Mais avec le grain « validation à la fin de la série », ce total vaut **0
// pendant toute la série** : le rappel demandé en S02 (« en permanence, c'est un bon rappel sur la
// cible ») affichait zéro exactement quand il servait. Relevé de l'axe saisie, `epics/EPIC-17`.
export function cumulSaisi(volees: readonly Volee[], table: PointsParZone): number {
  return volees.reduce((somme, volee) => somme + totalVolee(volee.valeurs, table), 0)
}

// La prochaine volée à saisir : la **plus petite** (1..nbVolees) pas encore **saisie**. Une volée
// est « faite » dès qu'elle est persistée — la **validation** (le verrou) est l'acte du scoreur, plus
// tard : le marqueur avance sans l'attendre. Si toutes sont saisies, on reste sur la **dernière**
// (l'édition d'une volée déjà saisie passe par le navigateur de volées, tant qu'elle n'est pas
// verrouillée — CA « édition avant validation »).
export function prochaineASaisir(volees: readonly Volee[], nbVolees: number, apres = 0): number {
  // ⚠️ **Une volée rendue par le scoreur passe devant** (E16US019). Sans cela, après une
  // annulation toutes les volées sont saisies, donc le pavé s'ouvrait sur la **dernière** du
  // barème — encore verrouillée — avec le message « sa correction relève du scoreur », c'est-à-dire
  // l'exact contraire de ce que le scoreur venait d'afficher.
  // ⚠️ `apres` est indispensable : `en_correction` ne tombe qu'à la **revalidation du scoreur**,
  // pas à la ressaisie. Sans lui, le pavé rouvrait en boucle la volée qu'on venait d'enregistrer,
  // et un lot de deux volées devenait infranchissable (relevé en revue).
  const rendue = volees.find((v) => v.en_correction && v.numero > apres)
  if (rendue !== undefined) return rendue.numero
  for (let numero = 1; numero <= nbVolees; numero += 1) {
    if (!volees.some((v) => v.numero === numero)) return numero
  }
  return nbVolees
}

// La volée déjà saisie portant ce numéro (pour pré-remplir le pavé lors d'une réédition), ou `null`.
export function voleeExistante(volees: readonly Volee[], numero: number): Volee | null {
  return volees.find((v) => v.numero === numero) ?? null
}

// Série mise à jour **optimiste** après une saisie mise en file hors-ligne (E04US009) : faute
// d'accusé serveur, on injecte la volée localement (`en_attente`) pour que le marqueur **continue**
// (la grille avance, `prochaineASaisir` passe à la suivante) au lieu de rester bloqué sur un écran
// d'erreur. La volée remplace celle du même numéro si elle existait. Le **cumul officiel** ne bouge
// pas : il ne compte que les volées **validées** (par le scoreur), et une volée en file ne l'est pas.
// À la reconnexion, la relecture serveur (`invalidateQueries`) remplace cet état par la vérité.
export function serieOptimiste(serie: Serie | undefined, corps: SaisirVolee): Serie {
  const base: Serie = serie ?? {
    tournoi_id: corps.tournoi_id,
    archer_id: corps.archer_id,
    cumul: 0,
    volees: [],
  }
  // ⚠️ Une volée **en correction** (E16US019) garde sa validation à la ressaisie, exactement comme
  // au serveur (`Serie.saisir_volee`) : la rendre « non validée » ici la ferait disparaître des
  // volées comptées à l'écran le temps de la reconnexion, alors que son score tient toujours.
  const remplacee = voleeExistante(base.volees, corps.numero)
  const enCorrection = remplacee?.en_correction === true
  const voleeEnAttente: Volee = {
    numero: corps.numero,
    valeurs: corps.valeurs,
    saisie_par: corps.saisie_par,
    validee_par: enCorrection ? remplacee.validee_par : null,
    verrouillee: false,
    en_correction: enCorrection,
    correction_ouverte_par: enCorrection ? remplacee.correction_ouverte_par : null,
    lot_validation: enCorrection ? remplacee.lot_validation : null,
    saisie_le: null,
    en_attente: true,
  }
  const volees = [...base.volees.filter((v) => v.numero !== corps.numero), voleeEnAttente].sort(
    (a, b) => a.numero - b.numero,
  )
  return { ...base, volees }
}

// Identifiant de saisie unique (idempotence ADR-0036), robuste **hors contexte sécurisé**.
// `crypto.randomUUID()` est réservé aux contextes sécurisés (HTTPS / `localhost`) ; or le
// déploiement jour J est un **LAN en http** (`http://<ip>` / `kervignarc.local`, cf.
// cahier-des-charges-technique §), où `randomUUID` est **absent** sur les tablettes — la saisie
// casserait alors silencieusement. `crypto.getRandomValues`, lui, est disponible partout : on bâtit
// un UUID v4 à la main dessus en repli. (Masqué en dev par `localhost`, d'où le repli explicite.)
export function nouvelIdentifiant(): string {
  const c = globalThis.crypto
  if (typeof c.randomUUID === 'function') return c.randomUUID()
  const octets = c.getRandomValues(new Uint8Array(16))
  octets[6] = ((octets[6] ?? 0) & 0x0f) | 0x40 // version 4
  octets[8] = ((octets[8] ?? 0) & 0x3f) | 0x80 // variante RFC 4122
  const hex = Array.from(octets, (o) => o.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

// Quelle volée viser **après** avoir enregistré `numeroActif` ? `null` = « rends la main au mode
// prochaine-à-saisir ». Fonction pure exprès : ce choix a porté deux défauts de suite, et il vivait
// dans un `onSuccess` que rien ne testait (revue).
//
// ⚠️ Deux pièges vécus : (a) une volée **rendue** reste `en_correction` jusqu'à la revalidation du
// scoreur — le mode automatique la rouvrirait en boucle ; (b) le repli de `prochaineASaisir` rend
// la **dernière du barème**, qui peut être verrouillée. On vise donc la suivante **encore en
// correction**, tous lots confondus, et à défaut on reste sur place.
export function voleeApresEnregistrement(
  volees: readonly Volee[],
  numeroActif: number,
): number | null {
  const active = volees.find((v) => v.numero === numeroActif)
  if (active?.en_correction !== true) return null
  return volees.find((v) => v.en_correction && v.numero > numeroActif)?.numero ?? numeroActif
}

// Le marqueur à envoyer avec une volée. Nouvelle volée : le marqueur actif la **signe**. Ré-édition
// d'une volée déjà saisie (`existante`) : `null`, pour que le domaine **préserve** le marqueur
// d'origine (`Serie.saisir_volee`, chemin « saisie_par is None ») — une correction ne réattribue pas
// la signature (CA « marqueur » : équivalent numérique de la signature FFTA).
export function quelSaisiePar(existante: Volee | null, marqueur: string | null): string | null {
  return existante !== null ? null : marqueur
}

// L'heure **locale** d'une saisie (« 10h42 ») depuis son horodatage ISO UTC, pour la consultation
// « volée N saisie par X à HHhMM » (CA « marqueur »). L'horodatage part du serveur en UTC
// (`HorlogeSysteme`) et s'affiche à l'heure murale de la salle (décalage TZ appliqué par `Date`).
// Chaîne vide si l'horodatage manque ou est illisible.
export function heureSaisie(iso: string | null): string {
  if (iso === null) return ''
  const instant = new Date(iso)
  if (Number.isNaN(instant.getTime())) return ''
  const hh = instant.getHours().toString().padStart(2, '0')
  const mm = instant.getMinutes().toString().padStart(2, '0')
  return `${hh}h${mm}`
}

// Libellé du grain de validation affiché au marqueur (D-11) : il dit **quand** le scoreur viendra.
export function libelleGrain(grain: Grain | null): string {
  if (grain === null) return 'Grain de validation non défini'
  switch (grain.grain) {
    case 'fin_de_serie':
      return 'Validation à la fin de la série'
    case 'fin_de_duel':
      return 'Validation à la fin du duel'
    case 'toutes_les_n_volees':
      return `Validation toutes les ${grain.n_volees ?? '?'} volées`
  }
}

// La volée ouverte pour un archer : celle qu'on a choisie (navigateur, case touchée), sinon la
// prochaine à saisir. ⚠️ **Le pavé et la ligne de l'archer actif la lisent ICI, tous les deux** :
// la recalculer d'un seul côté leur ferait montrer deux volées différentes dès qu'on navigue.
export function voleeOuverte(
  numeroChoisi: number | null,
  volees: readonly Volee[],
  nbVolees: number,
): number {
  return numeroChoisi ?? prochaineASaisir(volees, nbVolees)
}
