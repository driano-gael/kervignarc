// Tests de la **réserve d'honnêteté** de l'écran de composition (E05US020).
//
// Le bandeau prévient que ce qu'on compose ne se déroulera pas tel quel. Sa condition d'affichage
// empêche deux erreurs opposées : le laisser sur un déroulé désormais exact (faire douter d'un
// schéma juste), ou le retirer d'un déroulé que le moteur ne sait pas exécuter (laisser partir un
// tournoi qui ne se jouera pas). Les deux causes sont **distinctes** — un prélèvement inerte et un
// type non déroulé — et l'ancienne condition les couvrait toutes deux **par accident**.

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
    // type dont le moteur ne sait rien faire (DETTE-028). ⚠️ **Ce cas a changé de type trois fois**
    // (poules, suisse, colline), chaque US rendant jouable le format qu'il citait ; il vise donc le
    // **placement**. Ce qui est testé est le mécanisme, pas l'identité du type. ✅ **Et il cesse ici
    // de se déplacer** : le `placement` a un décor d'arbre mais aucun service pour le monter
    // (ADR-0083), état stable et non chantier en attente — ce test a enfin un porteur durable.
    render(
      <ReserveMoteur
        diagnostic={diagnostic([bloc('qualification'), bloc('placement', [flux('rangs')])])}
      />,
    )

    expect(bandeau()).not.toBeNull()
    // Le libellé du catalogue, pas la valeur d'énumération : c'est ce que l'organisateur lit.
    expect(bandeau()?.textContent).toContain('Placement')
  })

  it('ne prévient plus pour une colline, que le moteur déroule depuis E05US027', () => {
    // Le dernier des quatre formats d'E05US015 à être livré, et celui qui referme `DETTE-028` sur
    // son volet « moteurs sans appelant ». Même exigence que ses trois prédécesseurs : le signal
    // doit cesser de viser le format que l'US rend jouable, sans quoi il apprend à être ignoré.
    render(
      <ReserveMoteur
        diagnostic={diagnostic([bloc('qualification'), bloc('colline', [flux('rangs')])])}
      />,
    )

    expect(bandeau()).toBeNull()
  })

  it('ne prévient plus pour un système suisse, que le moteur déroule depuis E05US030', () => {
    // Même exigence qu'E05US023 pour les poules, un format plus loin : le moteur du suisse est
    // livré (E05US026) **et** ses écrans le sont (E05US030), donc l'avertissement mentirait.
    // Le placement, lui, reste visé — c'est le test ci-dessus.
    render(
      <ReserveMoteur
        diagnostic={diagnostic([bloc('qualification'), bloc('suisse', [flux('rangs')])])}
      />,
    )

    expect(bandeau()).toBeNull()
  })

  it('ne prévient plus pour des poules, que le moteur déroule depuis E05US023', () => {
    // Le CA d'E05US023 l'exigeait nommément : le signal doit cesser de viser les poules **et
    // continuer de viser** ce qui n'est pas joué — sans quoi il mentirait pour ceux qui restent. Un
    // avertissement qui survit à ce qu'il annonçait apprend à être ignoré. ⚠️ Les trois formats
    // qu'il citait alors (suisse, colline, Big Shoot Off) sont **tous livrés** depuis ; ce qui reste
    // visé est le placement et le barrage, dont le cas est d'une autre nature.
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
