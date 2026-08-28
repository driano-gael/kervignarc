// La **borne d'effectif** d'une phase au système suisse, dans l'atelier de composition (E05US030).
//
// ⚠️ **La fonction pure ne pouvait pas voir ce défaut** : `decrireBorne` n'a jamais eu tort, c'est
// l'**effectif qu'on lui donnait** qui était faux. L'atelier lui passait l'effectif **simulé du
// déroulé entier**, alors que la borne est opposée par `EtapeDeroule._verifier_rondes_appariables`
// sur l'effectif **déclaré de l'étape** — simuler 120 puis déclarer 8 affichait « 119 rondes au
// maximum », feu vert, et 422 à l'enregistrement. Le second cas garde le repli, **indicatif et non
// opposable**.

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { FormulaireEtape } from './Deroule'

function poser(effectifSimule: number | null) {
  render(
    <FormulaireEtape
      etape={{
        ordre: 1,
        type: 'suisse',
        bareme: null,
        validation: null,
        poules: null,
        big_shoot_off: null,
        suisse: { nb_rondes: 5 },
        colline: null,
        decoupage: null,
        sources: [],
        effectif: null,
        profondeur: null,
        // E05US033 : les deux réglages neufs, au défaut d'avant l'US.
        arrets: [],
        titre: null,
      }}
      etapesAmont={[]}
      surValider={vi.fn()}
      surAnnuler={() => {}}
      effectifSimule={effectifSimule}
    />,
  )
}

const declarerEffectif = (valeur: string) =>
  userEvent.type(screen.getByLabelText(/Effectif/), valeur)

describe('la borne d’effectif dans l’atelier', () => {
  it('se calcule sur l’effectif DÉCLARÉ de l’étape, pas sur la simulation', async () => {
    // Le cœur du défaut : 120 simulés, 8 déclarés. C'est 8 que le serveur opposera.
    poser(120)
    await declarerEffectif('8')

    expect(await screen.findByText(/8 archers : 7 rondes au maximum/)).toBeInTheDocument()
    expect(screen.queryByText(/119 rondes/)).toBeNull()
  })

  it('nomme l’écart quand le réglage dépasse la borne de l’étape', async () => {
    poser(120)
    await declarerEffectif('4')

    expect(
      await screen.findByText(/Vous en avez réglé 5 : les 3 premières seront jouées/),
    ).toBeInTheDocument()
  })

  it('retombe sur la simulation quand aucun effectif n’est déclaré', async () => {
    // Régime licite : le serveur ne vérifie alors **rien**, donc la phrase est une aide, pas une
    // promesse. Mieux vaut un repère approché que pas de repère du tout.
    poser(16)

    expect(await screen.findByText(/16 archers : 15 rondes au maximum/)).toBeInTheDocument()
  })

  it('n’annonce aucune borne quand rien ne permet de la calculer', () => {
    // Ni effectif déclaré, ni simulation : inventer un nombre serait pire que se taire.
    poser(null)

    expect(screen.queryByText(/rondes au maximum/)).toBeNull()
  })
})
