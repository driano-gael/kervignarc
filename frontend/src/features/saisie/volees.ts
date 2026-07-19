// Logique pure de la saisie (E04US002) — points, volée à saisir, libellé de grain.
//
// Isolée du rendu React pour être **testée** (vitest tourne en environnement node, sans DOM). Le
// serveur reste l'**autorité** (barème, zones, cumul officiel) : ces fonctions ne servent qu'à
// piloter l'affichage — total provisoire d'une volée en cours, quelle volée saisir, etc.

import type { Grain, Volee } from './api'

// Points d'une valeur de zone. `M` (manqué) = 0 ; les autres sont numériques (« 10 » → 10). Pas de
// « X » dans le vocabulaire FFTA retenu (cf. `domain/blason.ZoneScore`). Une valeur inattendue → 0
// (défensif : le pavé ne propose que des zones légales, mais on ne fait pas confiance à l'affichage).
export function pointsZone(valeur: string): number {
  if (valeur === 'M') return 0
  const points = Number.parseInt(valeur, 10)
  return Number.isNaN(points) ? 0 : points
}

// Total provisoire d'une volée en cours de frappe (avant enregistrement). Le cumul **officiel** de
// la série vient du serveur (volées validées uniquement) ; ceci n'est qu'un retour visuel immédiat.
export function totalVolee(valeurs: readonly string[]): number {
  return valeurs.reduce((somme, valeur) => somme + pointsZone(valeur), 0)
}

// La prochaine volée à saisir : la **plus petite** (1..nbVolees) pas encore **saisie**. Une volée
// est « faite » dès qu'elle est persistée — la **validation** (le verrou) est l'acte du scoreur, plus
// tard : le marqueur avance sans l'attendre. Si toutes sont saisies, on reste sur la **dernière**
// (l'édition d'une volée déjà saisie passe par le navigateur de volées, tant qu'elle n'est pas
// verrouillée — CA « édition avant validation »).
export function prochaineASaisir(volees: readonly Volee[], nbVolees: number): number {
  for (let numero = 1; numero <= nbVolees; numero += 1) {
    if (!volees.some((v) => v.numero === numero)) return numero
  }
  return nbVolees
}

// La volée déjà saisie portant ce numéro (pour pré-remplir le pavé lors d'une réédition), ou `null`.
export function voleeExistante(volees: readonly Volee[], numero: number): Volee | null {
  return volees.find((v) => v.numero === numero) ?? null
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

// L'heure locale d'une saisie (« 10:42 ») depuis son horodatage ISO UTC, pour la consultation
// « volée N saisie par X à HH:MM » (CA « marqueur »). Chaîne vide si l'horodatage manque ou est illisible.
export function heureSaisie(iso: string | null): string {
  if (iso === null) return ''
  const instant = new Date(iso)
  if (Number.isNaN(instant.getTime())) return ''
  const hh = instant.getHours().toString().padStart(2, '0')
  const mm = instant.getMinutes().toString().padStart(2, '0')
  return `${hh}:${mm}`
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
