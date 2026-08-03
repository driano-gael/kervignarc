// Tests de la mise en mots du palmarès (E06US004) — fonctions pures, sans React.
//
// Ce qui est vérifié ici est la règle d'affichage, pas le rendu : **aucun rang n'est inventé**
// (une fourchette reste une fourchette), l'origine du rang se dit, et ce qui n'est pas décidé se
// nomme. Ce sont les trois choses qu'un écran peut faire dire de faux à un palmarès juste.

import { describe, expect, it } from 'vitest'
import type { LignePalmares, PodiumCategorie } from './api'
import { detail, etatPodium, medaille, rang } from './presentation'

function ligne(partiel: Partial<LignePalmares> = {}): LignePalmares {
  return {
    rang_min: 1,
    rang_max: 1,
    rang_categorie_min: 1,
    rang_categorie_max: 1,
    archer_id: 1,
    nom: 'DUPONT',
    prenom: 'Jean',
    categorie_id: 1,
    categorie_libelle: 'Senior Homme',
    club_id: 1,
    origine: 'duels',
    statut: 'en_lice',
    ...partiel,
  }
}

describe('rang', () => {
  it('rend un rang exact en ordinal français', () => {
    expect(rang(1, 1)).toBe('1ᵉʳ')
    expect(rang(3, 3)).toBe('3ᵉ')
  })

  it('rend une fourchette telle quelle, sans choisir de chiffre', () => {
    // Le point de la règle : dans un tableau tronqué au podium, aucun match n'a départagé les
    // quatre battus des quarts. Afficher « 5ᵉ » ferait dire à l'écran ce que le tournoi n'a pas
    // décidé (ADR-0065, repris par ADR-0067).
    expect(rang(5, 8)).toBe('5ᵉ-8ᵉ')
  })

  it('rend un tiret pour un archer hors classement', () => {
    expect(rang(null, null)).toBe('—')
  })
})

describe('medaille', () => {
  it('nomme le métal des trois premiers', () => {
    expect(medaille(1)).toBe('Or')
    expect(medaille(2)).toBe('Argent')
    expect(medaille(3)).toBe('Bronze')
  })

  it('ne donne rien au 4ᵉ, qui figure au podium sans rien recevoir', () => {
    expect(medaille(4)).toBe('')
    expect(medaille(null)).toBe('')
  })
})

describe('detail', () => {
  it('ne dit rien du cas normal — un rang décerné en duel', () => {
    // Sur 120 lignes, répéter « duels » serait du bruit.
    expect(detail(ligne())).toBeNull()
  })

  it("dit « Qualification » pour un archer qui n'a pas disputé de duel", () => {
    // Sans cette mention, « 9ᵉ » laisse croire à une élimination en duel qui n'a pas eu lieu.
    expect(detail(ligne({ origine: 'qualification', rang_min: 9, rang_max: 9 }))).toBe(
      'Qualification',
    )
  })

  it('signale un rang encore à départager', () => {
    expect(detail(ligne({ rang_min: 5, rang_max: 8 }))).toBe('À départager')
  })

  it('fait primer le statut sur l’origine du rang', () => {
    // Un abandon (ADR-0050) est ce qu'il faut lire en premier : c'est ce qui explique la place.
    expect(detail(ligne({ statut: 'abandon', origine: 'qualification' }))).toBe('Abandon')
    expect(detail(ligne({ statut: 'disqualifie', rang_min: null, rang_max: null }))).toBe(
      'Disqualifié',
    )
  })
})

describe('etatPodium', () => {
  function podium(nb: number): PodiumCategorie {
    return {
      categorie_id: 1,
      categorie_libelle: 'Senior Homme',
      lignes: Array.from({ length: nb }, (_, i) => ligne({ archer_id: i + 1 })),
    }
  }

  it('nomme un podium vide plutôt que de laisser un blanc', () => {
    // Sur un écran projeté, un blanc se lit comme une panne d'affichage (`P-3`, E07US008).
    expect(etatPodium(podium(0))).toBe('Podium en cours — aucune place décernée.')
  })

  it('signale un podium partiel — le bronze se tire couramment avant l’or', () => {
    expect(etatPodium(podium(2))).toBe('Podium partiel — les finales ne sont pas toutes tirées.')
  })

  it('ne dit rien d’un podium complet', () => {
    expect(etatPodium(podium(3))).toBeNull()
    expect(etatPodium(podium(4))).toBeNull()
  })
})
