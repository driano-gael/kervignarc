// Tests de la dérivation pure du **verdict** d'un jalon (E16US012) — dérivés du CA.
//
// Source : `stories/E16-retours-maquettes.md`, E16US012 — « chaque écran répond à **une** question
// binaire » et « il **avertit sans bloquer** » (`D-15`). Deux exigences qui, ensemble, imposent
// **trois** formulations et non deux : « il manque quelque chose » ne se dit pas pareil selon que
// le serveur refusera ou laissera passer.

import { describe, expect, it } from 'vitest'
import { verdict } from './presentation'

describe('verdict d’un jalon', () => {
  it('CA — répond « oui » quand rien ne manque', () => {
    expect(verdict(true, true)).toEqual({ ton: 'ok', texte: 'Oui — rien ne s’y oppose.' })
  })

  it('CA — annonce un refus quand la garde est dure (démarrer)', () => {
    // `TournoiSansDepart`, `EffectifInsuffisantPourDemarrer` : le serveur refusera pour de bon.
    expect(verdict(false, true).texte).toContain('sera refusé')
  })

  it('CA — `D-15` : quand rien ne bloque, l’écran avertit sans annoncer de refus', () => {
    // Terminer n'a aucune garde dure. Annoncer « ce sera refusé » ferait un écran plus sévère que
    // le produit — et ferait renoncer un organisateur qui avait le droit de continuer.
    const { texte } = verdict(false, false)
    expect(texte).toContain('ne vous en empêchera pas')
    expect(texte).not.toContain('refusé')
  })

  it('les deux cas incomplets alertent, jamais en « ok »', () => {
    expect(verdict(false, true).ton).toBe('alerte')
    expect(verdict(false, false).ton).toBe('alerte')
  })

  it('le texte ne nomme aucun verbe de jalon', () => {
    // C'est ce qui permettra à `archiver` et `exporter` de se brancher sans le réécrire : le verbe
    // vit dans le titre de l'écran, pas dans le verdict. Sans cette contrainte, la « forme unique »
    // se serait dédoublée en quatre phrases au premier membre ajouté.
    for (const [pret, bloquant] of [
      [true, true],
      [false, true],
      [false, false],
    ] as const) {
      const { texte } = verdict(pret, bloquant)
      for (const verbe of ['démarrer', 'terminer', 'archiver', 'exporter']) {
        expect(texte).not.toContain(verbe)
      }
    }
  })
})
