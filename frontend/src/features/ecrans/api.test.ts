// Garde-fou des **bornes miroir** du réglage d'écran (correctif de revue E16US009).
//
// ⚠️ Ce fichier ne teste pas du comportement : il **épingle des constantes** — même patron que
// `pagination.test.ts` pour les *défauts*, oublié pour les *bornes* (relevé par trois axes). Le
// trou coûtait : resserrer `NOMS_PAR_PAGE_MAX` côté domaine laissait le formulaire proposer 100,
// donc un 422 sur un champ présenté comme valide ; l'élargir faisait interdire une valeur légale.
// Contrepartie serveur : `test_domain_ecran.py` épingle les mêmes six valeurs — garde-fou de
// **lecture**, pas de compilation (ADR-0098).

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
