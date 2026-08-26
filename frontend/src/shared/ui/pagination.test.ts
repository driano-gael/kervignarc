// Tests de la pagination de salle (retour maquettes du 04/08/2026, P06).
// Déplacés de `features/routage/` vers `shared/ui/` par E16US009, avec le module qu'ils couvrent.
// Les cas dérivent des phrases du questionnaire, citées dans `pagination.ts`.

import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  NOMS_PAR_PAGE,
  SECONDES_PAR_PAGE,
  nombreDePages,
  pageCourante,
  rateauDePage,
  trancheDePage,
  useSecondesDAffichage,
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

describe('les défauts du module et ceux du serveur', () => {
  it('valent exactement `ReglagePages.par_defaut()` côté serveur', () => {
    // ⚠️ **Garde-fou de la résorption de `DETTE-039`.** Le réglage vit désormais en base, mais un
    // écran non réglé retombe sur ces deux constantes : si elles divergeaient du défaut serveur,
    // le même écran s'afficherait différemment selon qu'il a reçu sa configuration ou non — et
    // personne dans la salle ne pourrait le diagnostiquer. Les deux valeurs sont épinglées ici et
    // dans `test_domain_ecran.py` (`test_le_reglage_de_pages_par_defaut_...`).
    expect(NOMS_PAR_PAGE).toBe(40)
    expect(SECONDES_PAR_PAGE).toBe(20)
  })
})

describe('useSecondesDAffichage — un cumul PAR vue', () => {
  // ⚠️ **Le défaut que ce test interdit est celui qu'E16US009 a trouvé en cours de route.** Le
  // cumul tenait au module, en une seule variable, sous ce commentaire : « une seule surface
  // projetée par onglet, donc pas de collision possible ». Vrai tant qu'**une** vue paginait. Dès
  // que le classement s'y est mis, les deux vues se partageaient le compteur : les pages du
  // classement avançaient pendant que l'écran montrait les affectations, et une page pouvait ne
  // jamais sortir — exactement le défaut qu'E07US008 avait déjà payé une fois.
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('ne reporte PAS le temps d’une vue sur celui d’une autre', () => {
    const premiere = renderHook(() => useSecondesDAffichage('classement'))
    act(() => {
      vi.advanceTimersByTime(30_000)
    })
    expect(premiere.result.current).toBeGreaterThan(0)
    premiere.unmount()

    const autre = renderHook(() => useSecondesDAffichage('affectations'))

    // La seconde vue démarre à zéro : elle n'a jamais été affichée.
    expect(autre.result.current).toBe(0)
    autre.unmount()
  })

  it('reprend le cumul de SA vue là où il s’était arrêté', () => {
    // L'autre moitié de la propriété : le temps d'affichage se **cumule** d'un passage à l'autre,
    // sans quoi la séquence de pages repartirait de la page 1 à chaque tour du déroulé et les
    // dernières pages ne sortiraient jamais.
    const premier = renderHook(() => useSecondesDAffichage('test'))
    act(() => {
      vi.advanceTimersByTime(20_000)
    })
    premier.unmount()

    const second = renderHook(() => useSecondesDAffichage('test'))
    act(() => {
      vi.advanceTimersByTime(1_000)
    })

    expect(second.result.current).toBeGreaterThanOrEqual(20)
    second.unmount()
  })
})
