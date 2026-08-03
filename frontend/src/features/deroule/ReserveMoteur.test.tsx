// Tests de la **réserve d'honnêteté** de l'écran de composition (E05US020).
//
// Le bandeau prévient l'organisateur que ce qu'il compose ne se déroulera pas tel quel. Sa
// condition d'affichage est la seule chose qui empêche deux erreurs opposées : le laisser sur un
// déroulé désormais exact (on fait douter d'un schéma juste), ou le retirer d'un déroulé que le
// moteur ne sait toujours pas exécuter (on laisse partir un tournoi qui ne se jouera pas).
//
// Les deux causes sont **distinctes** et doivent le rester : un prélèvement inerte (« le reste »,
// « les gagnants d'un tour ») et un type de phase que le moteur ne déroule pas (poules, suisse,
// colline). L'ancienne condition les couvrait toutes les deux **par accident** ; les séparer sans
// réintroduire la seconde était le défaut relevé en contre-revue.

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Bloc, Flux } from '../../shared/schema-braquets/modele'
import type { Diagnostic } from './api'
import { ReserveMoteur } from './Deroule'

function flux(nature: Flux['nature']): Flux {
  return {
    ordre_source: 1,
    ordre_cible: 2,
    nature,
    effectif: 8,
    rang_debut: 1,
    rang_fin: 8,
    tour: null,
    issue: null,
  }
}

function bloc(type: Bloc['type'], entrees: Flux[] = []): Bloc {
  return {
    ordre: 2,
    type,
    effectif: 8,
    tranche: null,
    nb_volees: null,
    nb_fleches_par_volee: null,
    tours: [],
    entrees,
    sorties: [],
    sans_suite: 0,
  }
}

function diagnostic(blocs: Bloc[]): Diagnostic {
  return { blocs, anomalies: [], flux: [] } as unknown as Diagnostic
}

const bandeau = () => screen.queryByRole('note')

describe('ReserveMoteur', () => {
  it('ne dit rien d’un déroulé entièrement honoré', () => {
    // Une qualification puis un tableau qui prélève **par rangs** : depuis E05US020, le moteur
    // l'exécute exactement. Laisser l'avertissement ferait douter d'un schéma juste.
    render(
      <ReserveMoteur
        diagnostic={diagnostic([
          bloc('qualification'),
          bloc('elimination_directe', [flux('rangs')]),
        ])}
      />,
    )

    expect(bandeau()).toBeNull()
  })

  it('prévient sur un prélèvement que le moteur ne sait pas honorer', () => {
    render(
      <ReserveMoteur
        diagnostic={diagnostic([
          bloc('qualification'),
          bloc('elimination_directe', [flux('reste')]),
        ])}
      />,
    )

    expect(bandeau()).not.toBeNull()
    expect(bandeau()?.textContent).toContain('le reste')
  })

  it('prévient aussi sur un type de phase que le moteur ne déroule pas', () => {
    // Le cas que la première version du correctif avait perdu : « qualification → poules », dont
    // le prélèvement est par rangs mais dont le moteur ne sait rien faire (DETTE-028).
    render(
      <ReserveMoteur
        diagnostic={diagnostic([bloc('qualification'), bloc('poules', [flux('rangs')])])}
      />,
    )

    expect(bandeau()).not.toBeNull()
    expect(bandeau()?.textContent).toContain('poules')
  })

  it('ne prévient pas pour un échauffement, qui ne produit rien par définition', () => {
    // « Sans point et sans classement » (§10.1) : le moteur n'a rien à y dérouler, ce n'est pas un
    // manque. L'y signaler serait du bruit sur un déroulé parfaitement valide.
    render(
      <ReserveMoteur
        diagnostic={diagnostic([bloc('echauffement'), bloc('qualification', [flux('rangs')])])}
      />,
    )

    expect(bandeau()).toBeNull()
  })
})
