// Test de rendu du bandeau hors ligne (E17US008, planche S09).
//
// ⚠️ **Monter le composant, pas `etatIndicateur`.** La règle qui décide de l'ouverture vit dans deux
// `return null` du composant, pas dans la fonction pure — un test de `etatIndicateur` resterait vert
// si l'un d'eux disparaissait. C'est le motif de `DETTE-085`, déjà cité par `Saisie.test.tsx`.
//
// L'oracle est le questionnaire `s09-etats-systeme.md` du 04/08/2026 : variante unique cochée,
// verdict ✅, et « l'aplat ambre plein est-il trop agressif ? » → **non**.

import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { useConnexionStore } from '../stores/connexionStore'
import { useFileHorsLigneStore } from '../stores/fileHorsLigneStore'
import { BandeauHorsLigne } from './BandeauHorsLigne'

function poser(statut: 'connexion' | 'connecte' | 'deconnecte', enAttente = 0, sync = false) {
  useConnexionStore.setState({ statut })
  useFileHorsLigneStore.setState({
    // Seule la **longueur** est lue par l'indicateur ; le contenu n'a pas à être plausible ici.
    enAttente: Array.from({ length: enAttente }, (_, i) => ({ identifiant_saisie: `x${i}` })),
    synchronisation: sync,
  } as never)
}

describe('BandeauHorsLigne', () => {
  beforeEach(() => poser('connecte'))

  it('hors ligne : un aplat pleine largeur qui dit que la saisie continue', () => {
    poser('deconnecte')
    render(<BandeauHorsLigne />)

    const bandeau = screen.getByRole('status')
    // La phrase que S02 appelle « la promesse la plus importante du produit » : un bandeau qui
    // nommerait seulement la panne ferait **arrêter** de saisir.
    expect(bandeau).toHaveTextContent(/la saisie continue/)
    expect(bandeau.className).toContain('bandeau-hors-ligne--deconnecte')
  })

  it('pendant la connexion initiale : aucun bandeau', () => {
    // Sans cette garde, le bandeau clignoterait à chaque arrivée sur un écran.
    poser('connexion')
    render(<BandeauHorsLigne />)

    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('synchronisation : le bandeau dit que les saisies repartent', () => {
    poser('connecte', 2, true)
    render(<BandeauHorsLigne />)

    const bandeau = screen.getByRole('status')
    expect(bandeau).toHaveTextContent(/repartent/)
    expect(bandeau.className).toContain('bandeau-hors-ligne--synchronisation')
  })

  it('lien rétabli et file encore pleine : aucun bandeau', () => {
    // ⚠️ Le cas qui a motivé la seconde garde (revue, axe C1). `etatIndicateur` rend `deconnecte`
    // dès que la file n'est pas vide, **quel que soit le lien** : sans cette garde, un rejeu
    // interrompu sur un transitoire laisserait « Hors ligne — la saisie continue » en travers de
    // l'écran alors que le réseau est revenu et que rien ne repartira. Faux sur les deux moitiés.
    poser('connecte', 2, false)
    render(<BandeauHorsLigne />)

    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })
})
