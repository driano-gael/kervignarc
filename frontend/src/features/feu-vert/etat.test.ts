import { describe, expect, it } from 'vitest'
import type { DuelAVenir, ResumeLancement } from './api'
import { afficheDuel, libelleBouton, libelleCibles, nomDuelliste } from './etat'

function duel(patch: Partial<DuelAVenir>): DuelAVenir {
  return {
    numero: 1,
    tour: 1,
    haut: { archer_id: 1, nom: 'Hood', prenom: 'Robin' },
    bas: { archer_id: 2, nom: 'Scarlet', prenom: 'Will' },
    participants_connus: true,
    cible_haut: 4,
    cible_bas: 4,
    cible_attribuee: true,
    sources_en_attente: [],
    pret_a_lancer: true,
    blocage: null,
    ...patch,
  }
}

describe('afficheDuel', () => {
  it('marque un duel prêt en vert', () => {
    expect(afficheDuel(duel({ pret_a_lancer: true }))).toEqual({ classe: 'pret', libelle: 'Prêt' })
  })

  it('nomme le blocage d’un duel en attente (jamais un simple drapeau)', () => {
    const bloque = duel({ pret_a_lancer: false, blocage: 'en attente du duel n°2' })
    expect(afficheDuel(bloque)).toEqual({ classe: 'attente', libelle: 'en attente du duel n°2' })
  })

  it('retombe sur un libellé générique si le blocage n’est pas renseigné', () => {
    expect(afficheDuel(duel({ pret_a_lancer: false, blocage: null }))).toEqual({
      classe: 'attente',
      libelle: 'En attente',
    })
  })
})

describe('nomDuelliste', () => {
  it('rend prénom + nom', () => {
    expect(nomDuelliste({ archer_id: 1, nom: 'Hood', prenom: 'Robin' })).toBe('Robin Hood')
  })

  it('rend « — » pour un camp sans occupant', () => {
    expect(nomDuelliste(null)).toBe('—')
  })
})

describe('libelleCibles', () => {
  it('rend une cible unique quand les deux duellistes la partagent', () => {
    expect(libelleCibles(duel({ cible_haut: 4, cible_bas: 4 }))).toBe('cible 4')
  })

  it('rend les deux cibles distinctes, triées', () => {
    expect(libelleCibles(duel({ cible_haut: 7, cible_bas: 4 }))).toBe('cibles 4 et 7')
  })

  it('rend une chaîne vide sans cible attribuée', () => {
    expect(libelleCibles(duel({ cible_haut: null, cible_bas: null }))).toBe('')
  })
})

describe('libelleBouton', () => {
  const impact = (patch: Partial<ResumeLancement>): ResumeLancement => ({
    phase_id: 1,
    numeros: [1, 2],
    cibles: [4, 7],
    nb_duels: 2,
    nb_archers: 4,
    ...patch,
  })

  it('chiffre ce que le bouton déclenche (duels, cibles, archers)', () => {
    expect(libelleBouton(impact({}))).toBe('Lancer — 2 duels · cibles 4, 7 · 4 archers prévenus')
  })

  it('accorde le singulier pour un seul duel', () => {
    expect(libelleBouton(impact({ numeros: [1], cibles: [4], nb_duels: 1, nb_archers: 2 }))).toBe(
      'Lancer — 1 duel · cibles 4 · 2 archers prévenus',
    )
  })

  it('rend null quand rien n’est prêt (bouton désactivé)', () => {
    expect(
      libelleBouton(impact({ numeros: [], cibles: [], nb_duels: 0, nb_archers: 0 })),
    ).toBeNull()
  })
})
