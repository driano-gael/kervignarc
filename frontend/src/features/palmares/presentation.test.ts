// Tests de la mise en mots du palmarès (E06US004) — fonctions pures, sans React.
//
// Ce qui est vérifié ici est la règle d'affichage, pas le rendu : **aucun rang n'est inventé**
// (une fourchette reste une fourchette), l'origine du rang se dit, et ce qui n'est pas décidé se
// nomme. Ce sont les trois choses qu'un écran peut faire dire de faux à un palmarès juste.

import { describe, expect, it } from 'vitest'
import type { LignePalmares, Podium } from './api'
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
    decerne: true,
    en_lice: false,
    ...partiel,
  }
}

describe('rang', () => {
  it('rend un rang exact en ordinal français', () => {
    expect(rang(1, 1)).toBe('1ᵉʳ')
    expect(rang(3, 3)).toBe('3ᵉ')
  })

  it('applique l’ordinal aux DEUX bornes — « 1ᵉʳ-2ᵉ », jamais « 1ᵉ-2ᵉ »', () => {
    // Le cas le plus regardé du palmarès : les deux finalistes, en tête de liste, tant que la
    // finale n'est pas tirée. Le test ne couvrait que `rang(5, 8)`, seule fourchette dont la
    // borne basse n'est pas 1 — la fixture évitait exactement la borne (relevé en revue).
    expect(rang(1, 2)).toBe('1ᵉʳ-2ᵉ')
    expect(rang(1, 4)).toBe('1ᵉʳ-4ᵉ')
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

  it('distingue « reste à tirer » d’un ex æquo définitif', () => {
    // Deux libellés, parce que ce sont deux situations opposées : la finale va trancher, ou plus
    // aucun match ne le fera. « Départager » est le vocabulaire du barrage (E06US003) — le dire à
    // deux finalistes annonce au public qu'une règle va décider à la place du tir.
    expect(detail(ligne({ rang_min: 1, rang_max: 2, en_lice: true, decerne: false }))).toBe(
      'Reste à tirer',
    )
    expect(detail(ligne({ rang_min: 5, rang_max: 8, decerne: false }))).toBe('Ex æquo')
  })

  it('signale un rang tranché par la politique et non par un match', () => {
    // Les quatre battus des quarts rangés sur leur qualification : le rang est unique, mais aucun
    // match ne l'a décerné — et c'est pour cela qu'ils ne montent pas sur le podium.
    expect(detail(ligne({ rang_min: 5, rang_max: 5, decerne: false }))).toBe(
      'Départagé au classement',
    )
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
  function podium(nb: number, effectif = 8, enAttente = true): Podium {
    return {
      portee: 'categorie',
      cle: 1,
      libelle: 'Senior Homme',
      effectif,
      en_attente: enAttente,
      places: Array.from({ length: nb }, (_, i) => ({
        rang: i + 1,
        ligne: ligne({ archer_id: i + 1 }),
      })),
    }
  }

  it('nomme un podium vide plutôt que de laisser un blanc', () => {
    // Sur un écran projeté, un blanc se lit comme une panne d'affichage (`P-3`, E07US008).
    expect(etatPodium(podium(0, 8, true), 4)).toBe('Podium en cours — aucune place décernée.')
  })

  it('signale un podium partiel — le bronze se tire couramment avant l’or', () => {
    expect(etatPodium(podium(2, 8, true), 4)).toBe(
      'Podium partiel — les finales ne sont pas toutes tirées.',
    )
  })

  it('ne dit rien d’un podium complet', () => {
    expect(etatPodium(podium(3, 8, true), 4)).toBeNull()
    expect(etatPodium(podium(4, 8, true), 4)).toBeNull()
  })

  it('ne dit pas « partiel » du podium complet d’une petite catégorie', () => {
    // Benjamine, Cadet Femme… : deux archers inscrits, podium complet à deux noms. Comparé à la
    // constante 3, le message « les finales ne sont pas toutes tirées » restait affiché à
    // perpétuité, tournoi terminé compris (relevé en revue).
    expect(etatPodium(podium(2, 2, true), 4)).toBeNull()
    expect(etatPodium(podium(1, 1, true), 4)).toBeNull()
  })
})

describe('etatPodium — profondeur réglée (E16US014)', () => {
  function podium(nb: number, effectif = 8, enAttente = true): Podium {
    return {
      portee: 'scratch',
      cle: null,
      libelle: 'Toutes catégories',
      effectif,
      en_attente: enAttente,
      places: Array.from({ length: nb }, (_, i) => ({
        rang: i + 1,
        ligne: ligne({ archer_id: i + 1 }),
      })),
    }
  }

  it('ne dit pas « partiel » d’un podium complet plus court que trois places', () => {
    // Profondeur 2 : deux places décernées, il n'en manque aucune. Comparer au 3 des médailles
    // aurait laissé « les finales ne sont pas toutes tirées » sur un podium terminé.
    expect(etatPodium(podium(2, 8, true), 2)).toBeNull()
  })

  it('garde le seuil des médailles quand la profondeur est plus grande', () => {
    // Profondeur 6 : le seuil reste 3 — le message parle des **médailles**, pas des places
    // affichées. Sans quoi tout podium complet de trois médaillés se serait dit « partiel ».
    expect(etatPodium(podium(3, 8, true), 6)).toBeNull()
  })
})

describe('etatPodium — attente réelle ou ex æquo (E16US014)', () => {
  function podium(nb: number, effectif = 5, enAttente = true): Podium {
    return {
      portee: 'club',
      cle: 7,
      libelle: 'Compagnie de Kervignarc',
      effectif,
      en_attente: enAttente,
      places: Array.from({ length: nb }, (_, i) => ({
        rang: i + 1,
        ligne: ligne({ archer_id: i + 1 }),
      })),
    }
  }

  it('ne promet pas des finales quand plus aucun match ne départagera', () => {
    // Portée club : la plupart des clubs n'ont personne au tableau (DETTE-028). Annoncer « les
    // finales ne sont pas toutes tirées » y est faux deux fois — ni finale de club, ni finale
    // restante — et le resterait tournoi terminé. ⚠️ Le message ne dit pas non plus « ex æquo » :
    // ces archers ont des rangs de qualification distincts (relevé par trois axes).
    expect(etatPodium(podium(0, 5, false), 4)).toBe(
      'Aucune place décernée — aucun duel n’a départagé ce groupe.',
    )
    expect(etatPodium(podium(1, 5, false), 4)).toBe(
      'Podium partiel — aucun duel n’a départagé les places restantes.',
    )
  })

  it('garde le message d’attente quand un archer du groupe a encore un match', () => {
    expect(etatPodium(podium(0, 5, true), 4)).toBe('Podium en cours — aucune place décernée.')
    expect(etatPodium(podium(1, 5, true), 4)).toBe(
      'Podium partiel — les finales ne sont pas toutes tirées.',
    )
  })
})
