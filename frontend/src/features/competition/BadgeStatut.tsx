// Pastille de statut du cycle de vie du tournoi — **présentation pure** du type `StatutTournoi`
// (partagé via `competition/api`). Elle vit ici, avec le type qu'elle rend, pour que **toute** feature
// l'importe sans dépendre de la feature `tournois` : `accueil` (tableau de bord) a besoin du badge, et
// `tournois` a besoin de la frise de `accueil` — placer le badge dans `tournois` créait un **cycle
// d'import** `accueil ↔ tournois` (revue E14US001). Le badge appartient au type, pas à un écran.

import type { StatutTournoi } from './api'

export function BadgeStatut({ statut }: { statut: StatutTournoi }) {
  // Les 7 statuts d'ADR-0026 (front aligné en E14US001). `Record` exhaustif : ajouter un statut sans
  // son libellé casse la compilation (TS strict) — le badge ne peut pas rester muet.
  const libelles: Record<StatutTournoi, string> = {
    brouillon: 'Brouillon',
    pret: 'Prêt',
    en_cours: 'En cours',
    en_pause: 'En pause',
    termine: 'Terminé',
    archive: 'Archivé',
    annule: 'Annulé',
  }
  return <span className={`badge badge--${statut.replace('_', '-')}`}>{libelles[statut]}</span>
}
