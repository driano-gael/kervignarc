// Tests de l'annonce du **plancher d'inscrits** sur l'écran de composition (E05US021).
//
// Le CA veut le minimum annoncé « qu'un effectif soit simulé ou non ». Le piège est le **registre**
// : annoncer un plancher n'est pas signaler un défaut — c'est une information neutre tant que rien
// ne cloche, et un avertissement ambre seulement quand l'effectif simulé passe dessous (`DV-03`,
// jamais la couleur seule : glyphe **et** mot). Se tromper de registre coûte des deux côtés : une
// alerte permanente apprend à les ignorer, pas d'alerte laisse simuler à 28 sans savoir qu'on ne
// pourra pas lancer.

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Diagnostic } from './api'
import { EffectifMinimum } from './Deroule'

function diagnostic(effectif_minimum: number, effectif: number | null): Diagnostic {
  return {
    effectif,
    applicable: true,
    blocs: [],
    anomalies: [],
    effectif_minimum,
  }
}

const alerte = () => screen.queryByRole('status')

describe('EffectifMinimum', () => {
  it('annonce le plancher sans effectif simulé', () => {
    // Le minimum est une propriété du **format**, pas de la simulation : il s'affiche d'emblée.
    render(<EffectifMinimum diagnostic={diagnostic(34, null)} />)

    expect(screen.getByText(/34 inscrits/)).toBeTruthy()
    expect(alerte()).toBeNull()
  })

  it('reste une information neutre quand l’effectif simulé suffit', () => {
    render(<EffectifMinimum diagnostic={diagnostic(34, 120)} />)

    expect(screen.getByText(/34 inscrits/)).toBeTruthy()
    expect(alerte()).toBeNull()
  })

  it('avertit dès que l’effectif simulé passe sous le plancher', () => {
    render(<EffectifMinimum diagnostic={diagnostic(34, 28)} />)

    const bandeau = alerte()
    expect(bandeau).not.toBeNull()
    // `D-16`/`P-4` : l'alerte chiffre son impact — les deux nombres, pas seulement « trop peu ».
    expect(bandeau?.textContent).toContain('28')
    expect(bandeau?.textContent).toContain('34')
    // `DV-03` : jamais la couleur seule — un mot porte aussi le sens.
    expect(bandeau?.textContent).toContain('À vérifier')
  })

  it('ne dit rien d’un format qui n’exige rien', () => {
    // Minimum 1 = tout déroulé accueille au moins un archer. L'afficher ferait passer une
    // trivialité pour une contrainte.
    render(<EffectifMinimum diagnostic={diagnostic(1, 120)} />)

    expect(screen.queryByText(/inscrits/)).toBeNull()
  })
})
