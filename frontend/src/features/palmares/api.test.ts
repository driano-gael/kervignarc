// Construction de l'URL du document de palmarès (E16US016) — logique **pure**, sans DOM ni réseau.
//
// ⚠️ Ce fichier existe parce que le renommage de route le plus risqué du lot n'était épinglé que
// côté serveur : `/tournois/{id}/palmares.pdf` a **disparu sans alias**. Une faute de frappe ici
// (chemin, `format` oublié, `?`/`&` inversé) donne un lien mort le jour J, sur la route publique
// remise aux archers — et la porte mécanique reste verte.

import { describe, expect, it } from 'vitest'
import { urlPalmaresDocument } from './api'

describe('urlPalmaresDocument', () => {
  it('vise la route généralisée et porte le format, même par défaut', () => {
    expect(urlPalmaresDocument(7)).toBe('/api/v1/tournois/7/palmares/document?format=pdf')
  })

  it('joint la catégorie avant le format, sur le même « ? »', () => {
    expect(urlPalmaresDocument(7, 3, 'csv')).toBe(
      '/api/v1/tournois/7/palmares/document?categorie_id=3&format=csv',
    )
  })

  it('ne porte plus aucune extension dans le chemin', () => {
    expect(urlPalmaresDocument(7, undefined, 'xlsx')).not.toContain('.pdf')
    expect(urlPalmaresDocument(7, undefined, 'xlsx')).toContain('format=xlsx')
  })
})
