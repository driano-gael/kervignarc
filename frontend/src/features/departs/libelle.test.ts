import { describe, expect, it } from 'vitest'
import { creneauDesDuels, creneauRetenu, libelleCreneau } from './libelle'

describe('libelleCreneau', () => {
  it('nomme un créneau par son numéro et son horaire', () => {
    expect(libelleCreneau({ id: 3, numero: 2, horaire: '14:00' })).toBe('Départ 2 — 14:00')
  })

  it('se passe de l’horaire quand il manque', () => {
    // L'horaire est obligatoire en base depuis la migration 0032, mais le DTO le laisse nullable :
    // concaténer sans garde afficherait « Départ 2 — null » sur les données d'avant.
    expect(libelleCreneau({ id: 3, numero: 2, horaire: null })).toBe('Départ 2')
  })
})

describe('creneauRetenu', () => {
  const matin = { id: 41, numero: 1, horaire: '09:00' }
  const apresMidi = { id: 42, numero: 2, horaire: '14:00' }
  const premier = (departs: readonly { id: number }[]) => departs[0]

  it('garde le choix de l’utilisateur quand le créneau existe encore', () => {
    expect(creneauRetenu([matin, apresMidi], 42, premier)).toBe(42)
  })

  it('retombe sur le défaut quand aucun choix n’a été fait', () => {
    expect(creneauRetenu([matin, apresMidi], null, premier)).toBe(41)
  })

  it('écarte un choix dont le créneau a disparu', () => {
    // **Le défaut corrigé** : l'écran gardait `42` en mémoire après la suppression du créneau (ou
    // un changement de tournoi) et continuait d'interroger le serveur sur un identifiant mort —
    // 404 permanent, ou liste vide qui se lit comme « rien à afficher ».
    expect(creneauRetenu([matin], 42, premier)).toBe(41)
  })

  it('rend null quand il n’y a plus aucun créneau', () => {
    expect(creneauRetenu([], 42, premier)).toBeNull()
  })
})

describe('creneauDesDuels', () => {
  // ⚠️ **La règle de l'écran de salle donnerait la mauvaise réponse au cas 2**, et c'est tout
  // l'objet de cette fonction : `EtatDepart` se dérive de la qualification seule, donc un créneau
  // passe `clos` à l'instant où ses duels commencent. Les trois cas ci-dessous sont les trois
  // moments d'une vraie journée à deux créneaux.
  const matin = (etat: string) => ({ id: 41, etat })
  const apresMidi = (etat: string) => ({ id: 42, etat })

  it('cas 1 — le matin tire, l’après-midi n’a pas commencé : on rend le matin', () => {
    expect(creneauDesDuels([matin('lance'), apresMidi('ouvert')])?.id).toBe(41)
  })

  it('cas 2 — la qualif du matin est close, l’après-midi tire : on rend LE MATIN', () => {
    // **Le défaut corrigé.** `departDeSalle` rendait ici l'après-midi (premier `lance`), alors que
    // les duels qu'on joue sont ceux du matin : les trois écrans affichaient « aucune phase à
    // élimination directe » pour le seul créneau où il y avait quelque chose à lancer.
    expect(creneauDesDuels([matin('clos'), apresMidi('lance')])?.id).toBe(41)
  })

  it('cas 3 — tout est clos : on rend le dernier, pas le premier', () => {
    expect(creneauDesDuels([matin('clos'), apresMidi('clos')])?.id).toBe(42)
  })

  it('avant que quiconque ait tiré, on rend le dernier plutôt que rien', () => {
    // Aucun `clos`, aucun `lance` : mieux vaut un créneau à montrer qu'un écran vide. Le sélecteur
    // reste là pour en changer.
    expect(creneauDesDuels([matin('ouvert'), apresMidi('ouvert')])?.id).toBe(42)
  })

  it('rend undefined sans aucun créneau', () => {
    expect(creneauDesDuels([])).toBeUndefined()
  })
})
