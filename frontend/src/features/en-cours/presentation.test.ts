// Tests de `phaseAAtterrir` — la règle d'atterrissage de l'onglet « En cours » (E05US031).
//
// **Dérivés du CA** : le commanditaire a demandé le 18/08/2026 un onglet « qui se place sur la
// phase en cours », avec remontée du déroulé. ⚠️ **Le régime de test avait été mal qualifié**
// (relevé axe B) : l'en-tête invoquait « API, repository, câblage : tests après l'implémentation »
// au motif que c'est une US d'écran — or `phaseAAtterrir` porte une **règle**, issue d'un CA
// antérieur au code. Deux cas (`en_pause`, `a_venir`) enregistraient un choix d'implémentation ;
// conservés parce que justes, mais rattachés à ce qu'ils gardent.

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

  it('préfère la phase démarrée la plus avancée à une phase amont restée ouverte', () => {
    // ⚠️ **Le défaut trouvé en revue (axes C1 et adversarial), et le seul cas qui vienne d'un
    // scénario de salle plutôt que du CA.** `StatutPhase` est **déclaratif** : aucun service de tir
    // ne le consulte, donc rien n'oblige à clore la phase 1 avant de démarrer la 2. Une
    // qualification qu'on oublie de passer à « Terminée » figeait l'onglet **et le projecteur** sur
    // « il n'y a pas de rencontre à suivre » pendant qu'on tirait les duels — sans recours, le fil
    // du déroulé étant masqué en salle.
    const phases = [phase(1, 'en_cours'), phase(2, 'en_cours'), phase(3, 'a_venir')]

    expect(phaseAAtterrir(phases)?.ordre).toBe(2)
  })

  it('retombe sur la première non terminée quand aucune phase n’est démarrée', () => {
    // Entre deux phases : la 1 est close, la 2 n'a pas été lancée. La règle 1 ne s'applique pas, la
    // règle 2 reprend la main — sans quoi le correctif ci-dessus aurait cassé le cas nominal du
    // matin.
    const phases = [phase(1, 'terminee'), phase(2, 'a_venir'), phase(3, 'a_venir')]

    expect(phaseAAtterrir(phases)?.ordre).toBe(2)
  })

  it('traite « en pause » comme non terminée', () => {
    // Une phase en pause est en cours d'exécution, simplement suspendue (pause déjeuner). La
    // sauter ferait afficher la phase suivante, qui n'a pas commencé, pendant tout le repas.
    const phases = [phase(1, 'terminee'), phase(2, 'en_pause'), phase(3, 'a_venir')]

    expect(phaseAAtterrir(phases)?.ordre).toBe(2)
  })
})
