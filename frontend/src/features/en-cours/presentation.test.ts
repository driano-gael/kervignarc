// Tests de `phaseAAtterrir` — la règle d'atterrissage de l'onglet « En cours » (E05US031).
//
// **Dérivés du CA**, pas de l'implémentation : le commanditaire a demandé, le 18/08/2026, un onglet
// « qui se place sur la phase en cours » avec la possibilité de remonter le déroulé du départ. Cette
// phrase se teste, et c'est ce qui est écrit ici — la fonction est ensuite libre de son moyen.
//
// ⚠️ **Honnêteté sur l'ordre** : cette US est une US d'écran, où la règle 9 place les tests après
// l'implémentation (« API, repository, câblage »). Ces cas-ci ont bien été écrits après le
// composant. Ce qui les protège du travers que la règle vise — un test qui ne fait que décrire le
// code — est leur **source** : les trois premiers sortent de la phrase du cadrage, le quatrième du
// besoin de salle déjà formulé par `VueTableaux` (« à 17 h, c'est le podium qu'on veut voir »).

import { describe, expect, it } from 'vitest'
import { phaseAAtterrir, type PhaseLisible } from './presentation'

function phase(ordre: number, statut: PhaseLisible['statut']): PhaseLisible {
  return { id: 100 + ordre, ordre, type: 'elimination_directe', statut }
}

describe('phaseAAtterrir — l’onglet s’ouvre sur ce qui se joue', () => {
  it('rend `null` quand le départ n’a aucune phase', () => {
    // Le déroulé n'est pas encore composé : l'onglet doit pouvoir le **dire**, donc distinguer ce
    // cas d'un chargement. Rendre la « première » d'une liste vide lèverait à la place.
    expect(phaseAAtterrir([])).toBeNull()
  })

  it('atterrit sur la première phase non terminée', () => {
    const phases = [phase(1, 'terminee'), phase(2, 'en_cours'), phase(3, 'a_venir')]

    expect(phaseAAtterrir(phases)?.ordre).toBe(2)
  })

  it('atterrit sur une phase pas encore lancée si elle est la première non terminée', () => {
    // Entre deux phases — la qualification est close, les duels ne sont pas partis. C'est le cas
    // que « la phase **en cours** » ne couvre pas littéralement, et il dure une bonne partie de la
    // matinée : montrer la phase à venir vaut mieux qu'un écran vide, et l'en-tête dit « pas encore
    // lancée » pour que personne ne croie le tir commencé.
    const phases = [phase(1, 'terminee'), phase(2, 'a_venir')]

    expect(phaseAAtterrir(phases)?.ordre).toBe(2)
  })

  it('atterrit sur la dernière phase quand tout est terminé', () => {
    // À 17 h le tournoi est fini : c'est le résultat de l'ultime phase que la salle regarde, pas un
    // écran vide. Même règle que `VueTableaux`, et pour la même raison.
    const phases = [phase(1, 'terminee'), phase(2, 'terminee'), phase(3, 'terminee')]

    expect(phaseAAtterrir(phases)?.ordre).toBe(3)
  })

  it('ne suppose pas que le serveur rend la liste triée', () => {
    // `ordre` est contigu 1..N par départ (ADR-0076), mais rien ne promet l'ordre de la réponse
    // JSON. Se fier à la position dans le tableau ferait atterrir sur une phase au hasard le jour
    // où le repository changerait son `ORDER BY` — un défaut invisible en revue de diff.
    const phases = [phase(3, 'a_venir'), phase(1, 'terminee'), phase(2, 'en_cours')]

    expect(phaseAAtterrir(phases)?.ordre).toBe(2)
  })

  it('traite « en pause » comme non terminée', () => {
    // Une phase en pause est en cours d'exécution, simplement suspendue (pause déjeuner). La
    // sauter ferait afficher la phase suivante, qui n'a pas commencé, pendant tout le repas.
    const phases = [phase(1, 'terminee'), phase(2, 'en_pause'), phase(3, 'a_venir')]

    expect(phaseAAtterrir(phases)?.ordre).toBe(2)
  })
})
