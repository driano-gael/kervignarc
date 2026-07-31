// Lecture des **prélèvements** d'une phase (E05US010, ADR-0061) — fonctions pures, testées.
//
// Extraites du composant `Phases.tsx` à la revue de l'US : ce sont trois règles de lecture (dont un
// garde-fou anti-perte de données), pas de la mise en page. Même geste que `ordre.ts` à côté, qui
// isole déjà le calcul de réordonnancement.

import type { SourcePhase } from './api'

// Décrit **un** prélèvement en clair, selon sa nature.
export function decrireSource(source: SourcePhase): string {
  const provenance = `de la phase ${source.ordre_source}`
  if (source.nature === 'reste') return `le reste ${provenance}`
  if (source.nature === 'issue_de_tour') {
    const cote = source.issue === 'perdants' ? 'perdants' : 'gagnants'
    return `${cote} du tour ${source.tour} ${provenance}`
  }
  // Fin ouverte : le format ne fige pas le dernier rang, il suit l'effectif réel. C'est ce qui
  // permet à un déroulé composé pour 120 archers d'en accueillir 82 sans être réécrit.
  if (source.rang_fin === null) return `rangs ${source.rang_debut} et suivants ${provenance}`
  return `rangs ${source.rang_debut} à ${source.rang_fin} ${provenance}`
}

// Décrit le peuplement complet d'une phase (ou son absence).
export function decrireSources(sources: SourcePhase[]): string {
  if (sources.length === 0) return 'alimentée par les inscriptions'
  return sources.map(decrireSource).join(', puis ')
}

// Une phase que le formulaire de cet écran sait éditer **sans rien perdre** : au plus un
// prélèvement, et de nature « par rangs ».
//
// Le formulaire n'en décrit qu'un seul ; le soumettre sur une phase à composition riche écraserait
// silencieusement le reste. D'où l'affichage en lecture seule — mieux vaut afficher que détruire.
// L'éditeur complet est E01US024.
export function editableIci(sources: SourcePhase[]): boolean {
  return sources.length <= 1 && sources.every((source) => source.nature === 'rangs')
}
