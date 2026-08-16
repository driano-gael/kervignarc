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
    // Le cas que la première version du correctif avait perdu : un prélèvement par rangs, mais un
    // type dont le moteur ne sait rien faire (DETTE-028).
    //
    // ⚠️ **Ce cas a déjà changé de type deux fois** : les poules jusqu'à E05US023, le système
    // suisse jusqu'à E05US030 — chaque US rendant jouable le format qu'il citait. Il vise donc
    // désormais la **colline**, dernier format que le moteur ne déroule pas (`E05US027`). Le
    // déplacement n'affaiblit rien : ce qui est testé est le mécanisme, pas l'identité du type — et
    // chaque type sorti de la liste gagne son propre test « ne prévient plus », ci-dessous, qui est
    // la moitié utile du changement.
    render(
      <ReserveMoteur
        diagnostic={diagnostic([bloc('qualification'), bloc('colline', [flux('rangs')])])}
      />,
    )

    expect(bandeau()).not.toBeNull()
    // Le libellé du catalogue, pas la valeur d'énumération : c'est ce que l'organisateur lit.
    expect(bandeau()?.textContent).toContain('Colline')
  })

  it('ne prévient plus pour un système suisse, que le moteur déroule depuis E05US030', () => {
    // Même exigence qu'E05US023 pour les poules, un format plus loin : le moteur du suisse est
    // livré (E05US026) **et** ses écrans le sont (E05US030), donc l'avertissement mentirait. La
    // colline, elle, reste visée — c'est le test ci-dessus.
    render(
      <ReserveMoteur
        diagnostic={diagnostic([bloc('qualification'), bloc('suisse', [flux('rangs')])])}
      />,
    )

    expect(bandeau()).toBeNull()
  })

  it('ne prévient plus pour des poules, que le moteur déroule depuis E05US023', () => {
    // Le CA d'E05US023 l'exige nommément : le signal doit cesser de viser les poules **et
    // continuer de viser** le suisse, la colline et le Big Shoot Off — sans quoi il mentirait pour
    // ceux qui restent. Un avertissement qui survit à ce qu'il annonçait apprend à être ignoré.
    render(
      <ReserveMoteur
        diagnostic={diagnostic([bloc('qualification'), bloc('poules', [flux('rangs')])])}
      />,
    )

    expect(bandeau()).toBeNull()
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
