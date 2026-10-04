// Tests des libellés de l'écran de saisie en duels (E00US024) : l'oracle est le texte affiché avant
// l'extraction, recopié tel quel.

import { describe, expect, it } from 'vitest'
import type { Camp, EquipeEcartee } from './api'
import {
  libelleMetaDuel,
  libelleSaisiesEnAttente,
  libelleStatut,
  motifsEcart,
  nomCamp,
  nomCourt,
  nomVainqueur,
  titreBarrage,
} from './presentation'

const ARCHER: Camp = { archer_id: 1, nom: 'DUPONT', prenom: 'Jean' }
const EQUIPE: Camp = { archer_id: null, nom: 'Les Flèches', prenom: '', membres: ['A', 'B'] }

describe('libelleStatut', () => {
  it('nomme chaque statut de la liste', () => {
    expect(libelleStatut('bye')).toBe('Exempt (bye)')
    expect(libelleStatut('attente_adversaires')).toBe('En attente des adversaires')
    expect(libelleStatut('a_saisir')).toBe('À saisir')
    expect(libelleStatut('en_cours')).toBe('En cours')
    expect(libelleStatut('a_valider')).toBe('À valider')
    expect(libelleStatut('valide')).toBe('Validé')
  })
})

describe('nomCamp', () => {
  it('nomme un archer « nom prénom »', () => {
    expect(nomCamp(ARCHER)).toBe('DUPONT Jean')
  })

  it('nomme une équipe avec ses membres', () => {
    expect(nomCamp(EQUIPE)).toBe('Les Flèches (A, B)')
  })

  it('nomme une équipe sans membres connus par son seul nom', () => {
    expect(nomCamp({ ...EQUIPE, membres: [] })).toBe('Les Flèches')
    expect(nomCamp({ archer_id: null, nom: 'Solo', prenom: '' })).toBe('Solo')
  })

  it('affiche un tiret pour un camp inconnu', () => {
    expect(nomCamp(null)).toBe('—')
  })
})

describe('nomCourt', () => {
  it('rend le nom seul d’un camp connu, archer comme équipe', () => {
    expect(nomCourt(ARCHER, 'haut')).toBe('DUPONT')
    expect(nomCourt(EQUIPE, 'bas')).toBe('Les Flèches')
  })

  it('rend le côté pour un camp inconnu', () => {
    expect(nomCourt(null, 'haut')).toBe('Haut')
    expect(nomCourt(null, 'bas')).toBe('Bas')
  })
})

describe('nomVainqueur', () => {
  const resultat = { points_haut: 6, points_bas: 2, termine: true, barrage_requis: false }

  it('nomme le camp vainqueur', () => {
    const duel = { haut: ARCHER, bas: EQUIPE }
    expect(nomVainqueur({ ...duel, resultat: { ...resultat, vainqueur: 'haut' } })).toBe('DUPONT')
    expect(nomVainqueur({ ...duel, resultat: { ...resultat, vainqueur: 'bas' } })).toBe(
      'Les Flèches',
    )
  })

  it('retombe sur le côté si le camp vainqueur est inconnu', () => {
    const duel = { haut: null, bas: null, resultat: { ...resultat, vainqueur: 'bas' as const } }
    expect(nomVainqueur(duel)).toBe('Bas')
  })

  it('aucun vainqueur sans résultat ou sans issue', () => {
    expect(nomVainqueur({ haut: ARCHER, bas: ARCHER, resultat: null })).toBeNull()
    expect(
      nomVainqueur({ haut: ARCHER, bas: ARCHER, resultat: { ...resultat, vainqueur: null } }),
    ).toBeNull()
  })
})

describe('motifsEcart', () => {
  const equipe: EquipeEcartee = { equipe_id: 1, nom: 'X', ecarts: [], membres_hors_course: [] }

  it('liste les membres hors course, séparés par un point-virgule', () => {
    expect(motifsEcart({ ...equipe, membres_hors_course: ['Ana', 'Bob'] })).toBe(
      'Ana n’est pas en lice dans ce départ (absent, forfait ou disqualifié) ; ' +
        'Bob n’est pas en lice dans ce départ (absent, forfait ou disqualifié)',
    )
  })

  it('place les écarts de conformité avant les membres, sans jamais le code brut', () => {
    const texte = motifsEcart({ ...equipe, ecarts: ['code_inconnu'], membres_hors_course: ['Ana'] })
    expect(texte.startsWith('Écart non reconnu ; Ana')).toBe(true)
  })

  it('rend une chaîne vide sans motif', () => {
    expect(motifsEcart(equipe)).toBe('')
  })
})

describe('libelleMetaDuel', () => {
  it('annonce le seuil de victoire en sets', () => {
    expect(libelleMetaDuel({ mode: 'sets', points_pour_gagner: 6 })).toBe(
      'Système de sets — premier à 6 points',
    )
  })

  it('n’annonce pas de seuil en cumul, ni en sets sans seuil connu', () => {
    expect(libelleMetaDuel({ mode: 'cumul', points_pour_gagner: 6 })).toBe('Cumul (arc à poulies)')
    expect(libelleMetaDuel({ mode: 'sets', points_pour_gagner: null })).toBe('Système de sets')
  })

  it('annote un duel dont un acte attend en file', () => {
    expect(libelleMetaDuel({ mode: 'cumul', points_pour_gagner: null, en_attente: true })).toBe(
      'Cumul (arc à poulies) · en attente d’envoi',
    )
    expect(libelleMetaDuel({ mode: null, points_pour_gagner: null, en_attente: false })).toBe('')
  })
})

describe('titreBarrage', () => {
  it('distingue la flèche unique des barrages à plusieurs flèches', () => {
    expect(titreBarrage(1)).toBe('Barrage (une flèche par archer, le plus près du centre)')
    expect(titreBarrage(3)).toBe(
      'Barrage (3 flèches par camp : le plus haut total, puis le plus près du centre)',
    )
  })
})

describe('libelleSaisiesEnAttente', () => {
  it('ne dit rien quand la file est vide', () => {
    expect(libelleSaisiesEnAttente(0)).toBeNull()
  })

  it('accorde au pluriel au-delà d’une saisie', () => {
    expect(libelleSaisiesEnAttente(1)).toBe('1 saisie en attente d’envoi')
    expect(libelleSaisiesEnAttente(2)).toBe('2 saisies en attente d’envoi')
  })
})
