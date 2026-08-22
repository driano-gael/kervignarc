// Le **découpage en tours** d'une qualification, sur l'atelier « Composer un format » (E05US035).
//
// ⚠️ **Ce fichier existe parce que la 2ᵉ passe de revue a montré que le seul écran portant le geste
// du CA n'avait aucun oracle.** L'écran des phases a le sien (`features/phases/Decoupage.test.tsx`),
// mais c'est ici — dans l'atelier de bibliothèque — que le découpage et la pause se composent
// ensemble sur une étape en cours de saisie, donc ici que la condition « la fiche de pauses s'ouvre
// dès qu'on tape 2, sans enregistrer » s'exerce réellement. Côté `Phases.tsx`, la même condition
// portait sur une phase persistée.
//
// Même leçon que `BorneSuisse.test.tsx` juste à côté : la fonction pure était juste, c'est ce qu'on
// lui donnait qui pouvait être faux.

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { Etape } from '../patrimoine/api'
import { FormulaireEtape } from './Deroule'

/** Une qualification en cours de composition : 20 volées de 3, non découpée. */
const QUALIFICATION: Etape = {
  ordre: 1,
  type: 'qualification',
  bareme: { nb_volees: 20, nb_fleches_par_volee: 3 },
  validation: { type: 'fin_de_serie', n_volees: null },
  poules: null,
  big_shoot_off: null,
  suisse: null,
  colline: null,
  decoupage: null,
  sources: [],
  effectif: null,
  profondeur: null,
  arrets: [],
  titre: null,
}

function poser(etape: Etape = QUALIFICATION) {
  const surValider = vi.fn()
  render(
    <FormulaireEtape
      etape={etape}
      etapesAmont={[]}
      surValider={surValider}
      surAnnuler={() => {}}
      effectifSimule={null}
    />,
  )
  return surValider
}

describe('le découpage en tours dans l’atelier de composition', () => {
  it('annonce ce que le découpage donne, sur le barème saisi dans le formulaire', async () => {
    // ⚠️ Ici le barème n'est pas celui d'un tournoi mais celui **du formulaire lui-même** : c'est le
    // pendant de l'effectif pour le suisse. Intervertir les deux sources ne casserait aucun test
    // pur — seul un test de rendu le voit.
    poser({ ...QUALIFICATION, decoupage: { nb_tours: 2 } })

    expect(await screen.findByText(/2 tours de 10 volées/)).toBeInTheDocument()
  })

  it('ouvre la fiche de pauses dès qu’on saisit 2 tours, sans enregistrement', async () => {
    // C'est le comportement que le commentaire de `Deroule.tsx` promet, et le seul endroit où la
    // condition d'arrêtabilité se lit sur un état **en cours de saisie**.
    poser()
    expect(screen.getByText(/Découpez-la d’abord en tours/)).toBeInTheDocument()

    const champ = screen.getByLabelText(/Nombre de tours/)
    await userEvent.clear(champ)
    await userEvent.type(champ, '2')

    expect(screen.queryByText(/Découpez-la d’abord en tours/)).not.toBeInTheDocument()
    expect(await screen.findByText(/2 tours de 10 volées/)).toBeInTheDocument()
  })

  it('n’offre pas de découpage sur un type qui n’est pas une qualification', () => {
    poser({ ...QUALIFICATION, type: 'suisse', bareme: null, suisse: { nb_rondes: 5 } })

    expect(screen.queryByText(/Découpage en tours/)).not.toBeInTheDocument()
  })

  it('nomme le refus quand le découpage ne tombe pas juste', async () => {
    poser({ ...QUALIFICATION, decoupage: { nb_tours: 3 } })

    expect(
      await screen.findByText(/20 volées ne se découpent pas en 3 tours égaux/),
    ).toBeInTheDocument()
  })
})
