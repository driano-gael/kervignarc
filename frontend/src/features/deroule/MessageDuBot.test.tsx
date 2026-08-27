// Ce que l'atelier dit d'une phase que **le bot de simulation** n'a pas jouée (E05US027).
//
// ⚠️ **Le même message a menti deux fois** (E05US028, E05US027, corrigés en revue) :
// `_TYPES_DEROULABLES` (serveur, ce que le **bot** sait simuler) et `MOTEUR_SAIT_JOUER` (front, ce
// que le **moteur** sait jouer) doivent rester d'accord, et seule la première moitié était faite —
// l'écran annonçant « le moteur ne sait pas dérouler ce type » pour un format tout juste rendu
// jouable. ⚠️ **Limite réelle** : ce fichier fige les quatre types du jour en dur, il attrape une
// régression, pas la prochaine récidive.

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { TypePhase } from '../../shared/phases/catalogue'
import type { PhaseSimulee } from './api'
import { LignePhaseSimulee } from './Deroule'

function nonJouee(type: TypePhase): PhaseSimulee {
  return {
    ordre: 2,
    type,
    effectif: 0,
    effectif_projete: 8,
    ecart: true,
    // Le cas qui nous intéresse : le bot n'a rien joué. C'est le régime NORMAL des quatre formats
    // à rencontres, pas un incident — d'où l'importance de ce que le message dit.
    joue: false,
    tours: 0,
    tours_projetes: 3,
    duels: 0,
    duels_projetes: 4,
  }
}

function rendre(type: TypePhase) {
  render(
    <table>
      <tbody>
        <LignePhaseSimulee phase={nonJouee(type)} />
      </tbody>
    </table>,
  )
}

describe('le message d’une phase que la simulation n’a pas jouée', () => {
  it.each(['poules', 'big_shoot_off', 'suisse', 'colline'] as const)(
    'dit que c’est la SIMULATION qui ne sait pas jouer une phase de type %s — pas le moteur',
    (type) => {
      rendre(type)

      expect(screen.getByRole('note')).toHaveTextContent(
        /la simulation ne sait pas encore jouer ce type de phase/,
      )
      // L'assertion qui compte vraiment : le vieux message ne doit PAS sortir. C'est lui qui ment,
      // et c'est lui qui revient dès qu'un type manque à `MOTEUR_SAIT_JOUER`.
      expect(screen.getByRole('note')).not.toHaveTextContent(/le moteur ne sait pas/)
    },
  )

  it('garde le message pessimiste pour un type que le moteur ne joue vraiment pas', () => {
    // La contrepartie, sans quoi le test ci-dessus serait satisfait en retirant le message tout
    // court : le placement n'a pas de service qui le monte, et là le vieux texte est exact.
    rendre('placement')

    expect(screen.getByRole('note')).toHaveTextContent(
      /le moteur ne sait pas encore dérouler ce type de phase/,
    )
  })
})
