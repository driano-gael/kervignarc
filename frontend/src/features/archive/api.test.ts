// Tests de la construction d'URL de l'archive (E11US003) — logique **pure**, sans DOM ni réseau.
// Le patron testable du projet : extraire la logique pure et la verrouiller ici. On vérifie que les
// cinq parties sont sérialisées en paramètres booléens, et que décocher une partie la passe à `false`.

import { describe, expect, it } from 'vitest'
import { cheminArchive, OPTIONS_ARCHIVE_DEFAUT } from './api'

describe('cheminArchive', () => {
  it('sérialise toutes les parties à true par défaut', () => {
    expect(cheminArchive(7, OPTIONS_ARCHIVE_DEFAUT)).toBe(
      '/api/v1/tournois/7/archive?base=true&donnees_csv=true&feuilles_de_marque=true' +
        '&liste_placement=true&liste_club_paiement=true',
    )
  })

  it('reflète une partie décochée en false', () => {
    expect(
      cheminArchive(7, { ...OPTIONS_ARCHIVE_DEFAUT, base: false, listeClubPaiement: false }),
    ).toBe(
      '/api/v1/tournois/7/archive?base=false&donnees_csv=true&feuilles_de_marque=true' +
        '&liste_placement=true&liste_club_paiement=false',
    )
  })
})
