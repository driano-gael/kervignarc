// Test de rendu du bandeau hors ligne (E17US008, planche S09).
//
// ⚠️ **Monter le composant, pas `etatIndicateur`.** La règle qui décide de l'ouverture vit dans le
// composant, pas dans la fonction pure — un test de `etatIndicateur` resterait vert si l'un des cas
// disparaissait. C'est le motif de `DETTE-085`, déjà cité par `Saisie.test.tsx`.
//
// L'oracle est le questionnaire `s09-etats-systeme.md` du 04/08/2026 : variante unique cochée,
// verdict ✅, et « l'aplat ambre plein est-il trop agressif ? » → **non**.

import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { useConnexionStore } from '../stores/connexionStore'
import { useFileHorsLigneStore, type VoleeEnFile } from '../stores/fileHorsLigneStore'
import { BandeauHorsLigne } from './BandeauHorsLigne'

// ⚠️ Fixture **typée** : un `as never` sur le `setState` éteindrait le contrôle de forme du store —
// un champ renommé poserait une clé morte, la file resterait vide, et le cas « lien rétabli et file
// pleine » passerait au vert **sans jamais avoir de file**. C'est le seul cas qui garde `DETTE-112`.
function volee(i: number): VoleeEnFile {
  return {
    tournoi_id: 1,
    archer_id: 12,
    numero: i + 1,
    valeurs: ['10', '9', '8'],
    saisie_par: 'DURAND',
    identifiant_saisie: `x${i}`,
  }
}

function poser(statut: 'connexion' | 'connecte' | 'deconnecte', enAttente = 0, sync = false) {
  useConnexionStore.setState({ statut })
  useFileHorsLigneStore.setState({
    enAttente: Array.from({ length: enAttente }, (_, i) => volee(i)),
    synchronisation: sync,
  })
}

describe('BandeauHorsLigne', () => {
  beforeEach(() => poser('connecte'))

  it('hors ligne : un aplat qui dit que la saisie continue', () => {
    poser('deconnecte')
    render(<BandeauHorsLigne />)

    const bandeau = screen.getByRole('status')
    // La phrase que S02 appelle « la promesse la plus importante du produit » : un bandeau qui
    // nommerait seulement la panne ferait **arrêter** de saisir.
    expect(bandeau).toHaveTextContent(/la saisie continue/)
    expect(bandeau.className).toContain('bandeau-hors-ligne--deconnecte')
  })

  it('hors ligne avec des saisies en attente : le compte est dit', () => {
    poser('deconnecte', 2)
    render(<BandeauHorsLigne />)

    expect(screen.getByRole('status')).toHaveTextContent(/2 saisies en attente/)
  })

  it('synchronisation : le bandeau dit que les saisies repartent', () => {
    poser('connecte', 2, true)
    render(<BandeauHorsLigne />)

    const bandeau = screen.getByRole('status')
    expect(bandeau).toHaveTextContent(/repartent/)
    expect(bandeau.className).toContain('bandeau-hors-ligne--synchronisation')
  })

  it('lien rétabli et file encore pleine : le bandeau DIT le compte, il ne se tait pas', () => {
    // ⚠️ Le cas qui ne se referme jamais (`DETTE-112`) : le rejeu s'arrête sur un transitoire et
    // n'écoute plus qu'une **transition** de statut, qui n'arrivera pas. Une 1ʳᵉ version rendait
    // `null` ici — elle remplaçait un message faux (« Hors ligne ») par **aucun** message, sur des
    // saisies jamais parties. Relevé en revue, axe C1.
    poser('connecte', 2)
    render(<BandeauHorsLigne />)

    const bandeau = screen.getByRole('status')
    expect(bandeau).toHaveTextContent(/2 saisies en attente d’envoi/)
    expect(bandeau).not.toHaveTextContent(/Hors ligne/)
  })

  it('pendant la connexion initiale, file pleine : le compte est dit aussi', () => {
    // La file est **persistée** : une tablette qui recharge après coupure arrive ici. Une garde qui
    // ne fermait que `statut === 'connecte'` laissait alors passer « Hors ligne », faux.
    poser('connexion', 3)
    render(<BandeauHorsLigne />)

    expect(screen.getByRole('status')).toHaveTextContent(/3 saisies en attente d’envoi/)
  })

  it('pendant la connexion initiale, rien en attente : aucun bandeau', () => {
    // Sans cette sortie, le bandeau clignoterait à chaque arrivée sur un écran.
    poser('connexion')
    render(<BandeauHorsLigne />)

    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })
})
