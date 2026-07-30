// Les trois axes de travail de l'admin et leur lecture depuis l'adresse (E14US003, ADR-0058).
//
// Séparé de `CoquilleAdmin.tsx` pour deux raisons : la règle ESLint `react-refresh/only-export-components`
// (un `.tsx` n'exporte que des composants — même parti que `features/poste/url.ts`), et parce que ces
// fonctions sont **pures**, donc testables sans rendu. C'est là que vivent les décisions ; la coquille
// n'en fait que l'affichage.

import type { DestinationAdminId } from './aide-ecrans'

// `besoinTournoi` dit si l'axe travaille **sur un tournoi**. L'atelier, non : c'est le patrimoine du
// club, il vit d'année en année — d'où l'absence de sélecteur de tournoi dans cet axe.
export type Axe = 'atelier' | 'pilotage' | 'gestion'

export const AXES: { axe: Axe; libelle: string; phrase: string; besoinTournoi: boolean }[] = [
  {
    axe: 'atelier',
    libelle: 'Atelier',
    phrase: 'Fabriquer : briques du club, salles types, formats de déroulé, banc d’essai.',
    besoinTournoi: false,
  },
  {
    axe: 'pilotage',
    libelle: 'Pilotage',
    phrase: 'Le temps réel : lancer, superviser, valider, faire tourner la journée.',
    besoinTournoi: true,
  },
  {
    axe: 'gestion',
    libelle: 'Gestion',
    phrase: 'L’administratif : inscriptions, paiements, exports, archives.',
    besoinTournoi: true,
  },
]

/**
 * Destination d'ouverture d'un axe.
 *
 * Pour le pilotage, c'est **l'accueil-tableau de bord** (`D-20`, E14US001) : c'est lui qui se
 * contextualise par statut (frise, checklist, chiffres), inutile donc d'aiguiller vers des écrans
 * différents selon le statut. Les autres destinations restent à un clic (`P-3`, priorité d'affichage,
 * pas restriction).
 */
export function destinationParDefaut(axe: Axe): DestinationAdminId {
  if (axe === 'pilotage') return 'accueil'
  if (axe === 'gestion') return 'inscriptions'
  return 'categories'
}

/**
 * L'axe nommé par les segments d'adresse, ou `null` pour l'accueil de l'admin.
 *
 * Un axe inconnu retombe sur `null` — donc sur l'accueil, jamais sur une page vide : une adresse mal
 * tapée doit rendre l'écran qui permet de repartir.
 */
export function axeDepuisSegments(segments: readonly string[]): Axe | null {
  const [premier] = segments
  return AXES.some((a) => a.axe === premier) ? (premier as Axe) : null
}

/**
 * La destination nommée par les segments, **validée** contre celles que l'axe propose réellement.
 *
 * Sans cette validation, une adresse comme `/admin/atelier/supervision` afficherait un écran de
 * pilotage sous l'intitulé « Atelier » — exactement le mélange que le découpage supprime.
 */
export function destinationDepuisSegments(
  segments: readonly string[],
  destinationsDeLAxe: readonly DestinationAdminId[],
): DestinationAdminId | null {
  const [, second] = segments
  return destinationsDeLAxe.find((d) => d === second) ?? null
}
