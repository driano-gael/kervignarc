// La jointure **étape du déroulé → phase d'un créneau**, par le rang (E16US002).
//
// ⚠️ **Module à part, et pas seulement pour le lint.** `Phase` (l'avancement dans un créneau) ne
// porte délibérément pas le titre : celui-ci décrit la **composition**, et le serveur ne le sert que
// sur `EtapeReponse` (ADR-0095 §3). Le pilotage doit donc joindre — et cette jointure était livrée
// sans aucune garde, `features/suivi-deroule/` n'ayant aucun harnais de test (relevé en 2ᵉ passe de
// revue par deux axes). L'extraire la rend testable sans monter l'écran.

import type { EtapeDeroule } from '../phases/api'

/** Le titre de chaque étape, indexé par son **rang**.
 *
 * Le rang **est** la clé de jointure entre une étape et ses instances (ADR-0076 §3 : les instances
 * d'un départ héritent de l'ordre des étapes) — `application/phases.py` l'écrit en toutes lettres,
 * et le réordonnancement comme la suppression réalignent les `Phase` de chaque départ.
 *
 * Rend une `Map` vide tant que les étapes ne sont pas chargées : chaque ligne retombe alors sur le
 * libellé de son type, soit le comportement d'avant l'US.
 */
export function titresParOrdre(etapes: EtapeDeroule[] | undefined): Map<number, string | null> {
  return new Map((etapes ?? []).map((etape) => [etape.ordre, etape.titre]))
}
