// Garde-fou des **bornes miroir** du réglage d'écran (correctif de revue E16US009).
//
// ⚠️ Ce fichier ne teste pas du comportement : il **épingle des constantes**. C'est délibéré, et
// c'est le même patron que `pagination.test.ts` pour les *défauts* — que l'US avait posé pour eux
// et oublié pour les *bornes*, alors que le raisonnement est identique. Trois axes de revue l'ont
// relevé.
//
// Ce que le trou coûtait, concrètement : resserrer `NOMS_PAR_PAGE_MAX` côté domaine laissait
// `<input max={100}>` dans le formulaire d'admin, donc l'organisateur saisissait une valeur que le
// serveur refusait ensuite en 422 sur un champ que l'UI présentait comme valide ; l'élargir laissait
// le formulaire interdire une valeur légale. Le serveur reste l'autorité (le coût est ergonomique,
// jamais fonctionnel) — mais un écart entre les deux ne se voit nulle part sans ce fichier, ni au
// typage ni au lint.
//
// Contrepartie côté serveur : `backend/tests/test_domain_ecran.py`
// (`test_les_bornes_du_reglage_de_pages_sont_inclusives`), qui épingle les mêmes six valeurs en
// littéraux. Les deux fichiers s'entre-citent : c'est un garde-fou de **lecture**, pas une
// contrainte de compilation — voir la note d'honnêteté du même nom dans ADR-0098.

import { describe, expect, it } from 'vitest'
import {
  CADENCE_MAX_S,
  CADENCE_MIN_S,
  CADENCE_PAGE_MAX_S,
  CADENCE_PAGE_MIN_S,
  NOMS_PAR_PAGE_MAX,
  NOMS_PAR_PAGE_MIN,
} from './api'

describe('les bornes du formulaire et celles du domaine', () => {
  it('valent exactement celles de `backend/domain/ecran.py`', () => {
    // Littéraux et non références croisées : une constante comparée à elle-même ne prouve rien.
    expect(NOMS_PAR_PAGE_MIN).toBe(5)
    expect(NOMS_PAR_PAGE_MAX).toBe(100)
    expect(CADENCE_PAGE_MIN_S).toBe(5)
    expect(CADENCE_PAGE_MAX_S).toBe(300)
  })

  it('vaut aussi pour les bornes de cadence de vue, dupliquées depuis E07US004', () => {
    // Le trou préexistait pour ces deux-là ; E16US009 en doublait le volume sans le fermer.
    expect(CADENCE_MIN_S).toBe(5)
    expect(CADENCE_MAX_S).toBe(3600)
  })
})
