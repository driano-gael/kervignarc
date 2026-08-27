// « Quel départ est en train de se jouer ? » — retour maquettes du 04/08/2026 (A02).
//
// Le commanditaire demande un bandeau permanent disant sur quel tournoi et quel départ on est. «
// Quel tournoi » est dans l'adresse ; « quel départ » ne l'était nulle part côté admin — l'écran
// `Departs` liste les créneaux, mais aucun ne disait lequel **compte maintenant**. La réponse se
// déduit des états déjà rendus par le serveur, sans nouvel endpoint : une règle de lecture, donc
// une fonction pure, donc testable (règle 9).

import type { Depart } from './api'

/** Le départ qui « compte maintenant », ou `null` si le tournoi n'a pas de créneau.
 *
 * Deux cas dans cet ordre : **un départ lancé** — s'il y en a plusieurs (deux créneaux menés de
 * front, rien ne l'interdit) on prend le plus petit numéro, le plus avancé ; sinon **le prochain à
 * ouvrir**, seule réponse utile avant le premier feu vert. ⚠️ Un tournoi dont tous les créneaux
 * sont `clos` rend `null` : dire « départ 3 » d'une journée finie serait faux.
 */
export function departCourant(departs: readonly Depart[]): Depart | null {
  const parNumero = (a: Depart, b: Depart) => a.numero - b.numero
  const lances = departs.filter((d) => d.etat === 'lance').sort(parNumero)
  if (lances.length > 0) return lances[0] ?? null
  const ouverts = departs.filter((d) => d.etat === 'ouvert').sort(parNumero)
  return ouverts[0] ?? null
}

/** Ce que le bandeau écrit à côté du numéro : l'état, en toutes lettres. `DV-03` — le mot porte le
 * sens, la couleur ne fait que le renforcer. */
export function libelleEtatDepart(depart: Depart): string {
  if (depart.etat === 'lance') return 'en cours'
  if (depart.etat === 'ouvert') return 'à lancer'
  return 'clos'
}
