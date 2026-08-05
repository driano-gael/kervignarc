// Tests de la pagination de salle (retour maquettes du 04/08/2026, P06).
// Les cas dérivent des phrases du questionnaire, citées dans `pagination.ts`.

import { describe, expect, it } from 'vitest'
import {
  NOMS_PAR_PAGE,
  nombreDePages,
  pageCourante,
  rateauDePage,
  trancheDePage,
} from './pagination'

describe('nombreDePages', () => {
  it('une liste vide a **une** page — celle qui dit qu’elle est vide', () => {
    expect(nombreDePages(0)).toBe(1)
  })

  it('une liste qui tient sur un écran n’en a qu’une', () => {
    expect(nombreDePages(NOMS_PAR_PAGE)).toBe(1)
  })

  it('un seul nom de trop fait une page de plus', () => {
    expect(nombreDePages(NOMS_PAR_PAGE + 1)).toBe(2)
  })

  it('200 archers — le cas que le code disait ne pas savoir traiter', () => {
    expect(nombreDePages(200, 40)).toBe(5)
  })
})

describe('pageCourante', () => {
  it('une seule page ne tourne pas', () => {
    expect(pageCourante(1, 999)).toBe(0)
  })

  it('avance d’une page toutes les 20 s', () => {
    expect(pageCourante(5, 0, 20)).toBe(0)
    expect(pageCourante(5, 19, 20)).toBe(0)
    expect(pageCourante(5, 20, 20)).toBe(1)
    expect(pageCourante(5, 41, 20)).toBe(2)
  })

  it('boucle après la dernière page', () => {
    expect(pageCourante(3, 60, 20)).toBe(0)
    expect(pageCourante(3, 80, 20)).toBe(1)
  })

  it('survit à une horloge qui recule (mise à l’heure en cours de journée)', () => {
    // L'invariant qui compte est **le domaine**, pas la valeur : un index négatif sortirait de la
    // liste et laisserait l'écran vide, sans personne devant pour le remarquer. Un temps négatif
    // retombe donc sur le cycle précédent — la dernière page — et jamais en dehors.
    for (const secondes of [-1, -20, -21, -1000]) {
      const page = pageCourante(3, secondes, 20)
      expect(page).toBeGreaterThanOrEqual(0)
      expect(page).toBeLessThan(3)
    }
    expect(pageCourante(3, -20, 20)).toBe(2)
  })

  it('deux instants du même cycle donnent la même page ; le cycle suivant en donne une autre', () => {
    // ⚠️ La première version de ce test comparait **le même appel à lui-même** — vrai pour
    // n'importe quelle fonction déterministe, y compris une qui aurait cassé la propriété annoncée
    // par son titre (relevé par trois axes de revue le 05/08/2026). On compare désormais des
    // instants **distincts**, ce qui est la seule façon de tester une découpe du temps.
    expect(pageCourante(4, 40, 20)).toBe(pageCourante(4, 55, 20))
    expect(pageCourante(4, 40, 20)).not.toBe(pageCourante(4, 60, 20))
  })
})

describe('trancheDePage', () => {
  const noms = ['A', 'B', 'C', 'D', 'E']

  it('découpe dans l’ordre', () => {
    expect(trancheDePage(noms, 0, 2)).toEqual(['A', 'B'])
    expect(trancheDePage(noms, 1, 2)).toEqual(['C', 'D'])
  })

  it('la dernière page peut être incomplète', () => {
    expect(trancheDePage(noms, 2, 2)).toEqual(['E'])
  })

  it('une page hors bornes rend une liste vide, jamais `undefined`', () => {
    // Un écran que personne ne surveille ne doit pas planter sur un `.map`.
    expect(trancheDePage(noms, 99, 2)).toEqual([])
  })
})

describe('rateauDePage', () => {
  it('donne les bornes de la page, en trois lettres', () => {
    expect(rateauDePage(['DUPONT', 'DURAND', 'LEFEVRE'])).toEqual({ debut: 'DUP', fin: 'LEF' })
  })

  it('trois lettres et non l’initiale : « L → L » ne distinguerait rien', () => {
    expect(rateauDePage(['LEBLANC', 'LEROY'])).toEqual({ debut: 'LEB', fin: 'LER' })
  })

  it('un nom plus court que trois lettres passe tel quel', () => {
    expect(rateauDePage(['LI', 'ZOLA'])).toEqual({ debut: 'LI', fin: 'ZOL' })
  })

  it('une page vide n’a pas de râteau', () => {
    expect(rateauDePage([])).toBeNull()
  })
})
