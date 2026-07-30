import { describe, expect, it } from 'vitest'
import type { ProchainDuel, RoutageArcher } from './api'
import { adversaire, destination, detail, rang, serieClose, titre } from './presentation'

function prochain(patch: Partial<ProchainDuel> = {}): ProchainDuel {
  return {
    numero: 1,
    tour: 1,
    libelle: 'Demi-finale',
    cible: 4,
    position: 'B',
    adversaire: { archer_id: 2, nom: 'DUPONT', prenom: 'Jean' },
    sources_en_attente: [],
    manque: null,
    ...patch,
  }
}

function archer(patch: Partial<RoutageArcher> = {}): RoutageArcher {
  return {
    archer_id: 1,
    nom: 'MARTIN',
    prenom: 'Léa',
    issue: 'prochain_duel',
    prochain: prochain(),
    rang_final: null,
    tour_sortie: null,
    motif: null,
    ...patch,
  }
}

describe('destination', () => {
  it('donne la cible et la place', () => {
    expect(destination(prochain())).toBe('Cible 4 · place B')
  })

  it('tolère une cible sans position', () => {
    expect(destination(prochain({ position: null }))).toBe('Cible 4')
  })

  it('rend null quand la cible n’est pas encore attribuée', () => {
    // Tour ≥ 2 : le placement intégral 1→N est E05US010. Surtout pas la cible du tour 1, qui serait
    // périmée — c'est le panneau qui enverrait le finaliste sur son ancienne butte.
    expect(destination(prochain({ cible: null, position: null }))).toBeNull()
  })
})

describe('adversaire', () => {
  it('nomme l’adversaire quand il est connu', () => {
    expect(adversaire(prochain())).toBe('DUPONT Jean')
  })

  it('nomme le duel attendu plutôt que de laisser un blanc', () => {
    const attente = prochain({ adversaire: null, sources_en_attente: [2] })
    expect(adversaire(attente)).toBe('en attente du duel n°2')
  })

  it('cumule les sources quand les deux camps sont en attente', () => {
    const attente = prochain({ adversaire: null, sources_en_attente: [2, 3] })
    expect(adversaire(attente)).toBe('en attente du duel n°2, n°3')
  })
})

describe('rang', () => {
  it('dit « vainqueur » plutôt que « 1ᵉ »', () => {
    expect(rang(archer({ rang_final: 1 }))).toBe('Vainqueur du tableau')
  })

  it('ordonne les autres places du podium', () => {
    expect(rang(archer({ rang_final: 3 }))).toBe('3ᵉ du tableau')
  })

  it('n’invente aucun rang tant qu’il n’est pas acquis', () => {
    // Les rangs intermédiaires (9-16ᵉ…) supposent l'agrégation d'E06US004, non livrée.
    expect(rang(archer({ rang_final: null }))).toBeNull()
  })
})

describe('titre', () => {
  it('met la destination en avant — c’est ce que l’archer vient chercher', () => {
    expect(titre(archer())).toBe('Cible 4 · place B')
  })

  it('retombe sur le tour quand la cible n’est pas encore connue', () => {
    expect(titre(archer({ prochain: prochain({ cible: null, position: null }) }))).toBe(
      'Demi-finale',
    )
  })

  it('annonce le rang acquis', () => {
    expect(titre(archer({ issue: 'termine', prochain: null, rang_final: 2 }))).toBe('2ᵉ du tableau')
  })

  it('dit où l’archer est sorti quand son rang n’est pas encore publié', () => {
    const sorti = archer({
      issue: 'termine',
      prochain: null,
      tour_sortie: 'Quart de finale',
      motif: 'rang publié en fin de phase',
    })
    expect(titre(sorti)).toBe('Éliminé — Quart de finale')
  })

  it('avoue l’ignorance plutôt que d’afficher un vide', () => {
    const inconnu = archer({ issue: 'indisponible', prochain: null, motif: 'non retenu' })
    expect(titre(inconnu)).toBe('Destination inconnue')
  })
})

describe('detail', () => {
  it('donne le tour et l’adversaire quand tout est connu', () => {
    expect(detail(archer())).toBe('Demi-finale · DUPONT Jean')
  })

  it('remonte le motif du serveur quand la cible manque, sans répéter le tour', () => {
    const sansCible = archer({
      prochain: prochain({
        cible: null,
        position: null,
        manque: 'cible attribuée au lancement du tour',
      }),
    })
    expect(detail(sansCible)).toBe('cible attribuée au lancement du tour · DUPONT Jean')
  })

  it('remonte le motif du serveur pour une issue terminée', () => {
    const sorti = archer({ issue: 'termine', prochain: null, motif: 'rang publié en fin de phase' })
    expect(detail(sorti)).toBe('rang publié en fin de phase')
  })
})

describe('serieClose', () => {
  const validee = { verrouillee: true }
  const saisie = { verrouillee: false }

  it('est close quand toutes les volées du barème sont validées', () => {
    expect(serieClose([validee, validee], 2)).toBe(true)
  })

  it('n’est pas close tant qu’il reste des volées à tirer', () => {
    expect(serieClose([validee], 2)).toBe(false)
  })

  it('n’est pas close si une volée est saisie mais pas validée', () => {
    // C'est le scoreur qui clôt une série, pas le marqueur : un tir non validé ne route personne.
    expect(serieClose([validee, saisie], 2)).toBe(false)
  })

  it('n’est pas close tant que le barème est inconnu', () => {
    expect(serieClose([validee, validee], null)).toBe(false)
  })
})
