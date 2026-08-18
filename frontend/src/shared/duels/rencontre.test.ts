// Tests de la lecture **publique** d'une rencontre (E05US031).
//
// Ce que ces cas gardent n'est pas de la mise en forme : c'est la frontière entre « le tir est allé
// au bout » et « le scoreur a scellé », que le DTO public transporte en deux booléens distincts et
// que les trois formats doivent rendre de la même façon. Un écran qui les confond annonce un
// vainqueur qu'une correction peut encore renverser.

import { describe, expect, it } from 'vitest'
import {
  etatRencontre,
  gagnantAffiche,
  nomComplet,
  participants,
  scoreRencontre,
  type RencontreLisible,
} from './rencontre'

function rencontre(patch: Partial<RencontreLisible> = {}): RencontreLisible {
  return {
    haut: { archer_id: 1, nom: 'MARTIN', prenom: 'Luc' },
    bas: { archer_id: 2, nom: 'DURAND', prenom: 'Aline' },
    points_haut: null,
    points_bas: null,
    vainqueur: null,
    termine: false,
    validee: false,
    desynchronisee: false,
    ...patch,
  }
}

describe('etatRencontre — ce que le public lit de l’avancement', () => {
  it('dit « à tirer » tant que rien n’est joué', () => {
    expect(etatRencontre(rencontre())).toBe('à tirer')
  })

  it('dit « en attente de validation » entre la fin du tir et le sceau', () => {
    // C'est l'intervalle que `termine` et `validee` séparent, et il peut durer longtemps : le
    // scoreur descend la ligne feuille par feuille. Le taire ferait lire un score définitif.
    expect(etatRencontre(rencontre({ termine: true, points_haut: 6, points_bas: 2 }))).toBe(
      'en attente de validation',
    )
  })

  it('dit « validée » une fois scellée', () => {
    expect(etatRencontre(rencontre({ termine: true, validee: true }))).toBe('validée')
  })

  it('donne la désynchronisation la priorité sur tout le reste', () => {
    // Une rencontre dont le tir a été mis de côté (la composition a bougé sous un score saisi) est
    // **bloquée**, pas « à tirer ». L'annoncer autrement ferait attendre des archers pour rien.
    expect(etatRencontre(rencontre({ desynchronisee: true }))).toBe('tir mis de côté')
    expect(etatRencontre(rencontre({ desynchronisee: true, validee: true }))).toBe(
      'tir mis de côté',
    )
  })
})

describe('scoreRencontre — le score dès qu’il existe, pas dès qu’il est scellé', () => {
  it('rend `null` tant que les deux points ne sont pas là', () => {
    expect(scoreRencontre(rencontre())).toBeNull()
    expect(scoreRencontre(rencontre({ points_haut: 6 }))).toBeNull()
  })

  it('rend le score d’une rencontre terminée mais non validée', () => {
    // C'est ce que la salle voit sur les cibles : attendre le sceau ferait mentir l'écran pendant
    // toute la tournée du scoreur. L'état de la rencontre, lui, dit que ce n'est pas définitif.
    expect(scoreRencontre(rencontre({ termine: true, points_haut: 6, points_bas: 2 }))).toBe(
      '6 — 2',
    )
  })

  it('rend un score nul sans le confondre avec une absence de score', () => {
    // `0 — 0` est un score réel (aucun set gagné de part et d'autre à ce stade). Un test de
    // véracité (`if (!points)`) l'aurait effacé — le genre de bug qui ne se voit qu'en salle.
    expect(scoreRencontre(rencontre({ points_haut: 0, points_bas: 0 }))).toBe('0 — 0')
  })
})

describe('gagnantAffiche — jamais avant le sceau', () => {
  it('ne désigne personne tant que la rencontre n’est pas validée', () => {
    // Le serveur remplit `vainqueur` dès la fin du tir ; le mettre en gras avant validation
    // annoncerait un résultat qu'une correction peut renverser.
    expect(gagnantAffiche(rencontre({ termine: true, vainqueur: 'haut' }))).toBeNull()
  })

  it('désigne le côté vainqueur une fois validée', () => {
    expect(gagnantAffiche(rencontre({ termine: true, validee: true, vainqueur: 'bas' }))).toBe(
      'bas',
    )
  })

  it('ne désigne personne sur une valeur inconnue', () => {
    // Un `vainqueur` hors des deux côtés attendus (nul en attente de barrage, serveur plus récent)
    // ne doit mettre **aucun** nom en gras plutôt que d'en choisir un par défaut.
    expect(gagnantAffiche(rencontre({ validee: true, vainqueur: 'egalite' }))).toBeNull()
  })
})

describe('participants — savoir si un archer suivi tire ici', () => {
  it('rend les deux duellistes', () => {
    expect(participants(rencontre())).toEqual([1, 2])
  })

  it('ignore un côté vide sans décaler la liste', () => {
    // Un bye, ou une place qu'aucune phase amont n'a encore attribuée : la rencontre existe avec un
    // seul nom. Rendre `null` dans la liste ferait « suivre » un archer inexistant.
    expect(participants(rencontre({ bas: null }))).toEqual([1])
  })
})

describe('nomComplet', () => {
  it('assemble prénom et nom', () => {
    expect(nomComplet({ archer_id: 1, nom: 'MARTIN', prenom: 'Luc' })).toBe('Luc MARTIN')
  })

  it('ne laisse pas d’espace en tête quand le prénom manque', () => {
    // L'import tolère un prénom vide ; « ␣MARTIN » se voit à l'écran et décale la colonne.
    expect(nomComplet({ archer_id: 1, nom: 'MARTIN', prenom: '' })).toBe('MARTIN')
  })
})
