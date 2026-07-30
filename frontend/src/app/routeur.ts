// Routeur **maison** de l'application (E14US003) — analyse et construction de chemins, sans dépendance.
//
// **Pourquoi maison.** L'arbitrage du 18/07/2026 (« pas de react-router, le périmètre ne justifie pas
// la dépendance ») avait été **levé** par le commanditaire le 30/07 au profit de `react-router-dom` —
// puis deux faits l'ont refermé le jour même : (1) toutes les versions ≥ 7.12.0 tirent un
// `react-router` dans la plage vulnérable de l'avis `GHSA-qwww-vcr4-c8h2`, ce qui contredit la
// règle 11 (« `npm audit` vert ») même si le trou vise le mode RSC, absent d'une SPA purement
// cliente ; (2) l'installation est bloquée sur le poste. Le besoin réel — cinq mondes et deux
// segments d'admin — tient en quelques dizaines de lignes : la règle 11 dit précisément « stdlib ou
// quelques lignes maison préférées ». Décision : ADR-0059. Dette inscrite : **DETTE-024**.
//
// **Ce module est pur** (aucun accès au DOM) : c'est lui qui porte les décisions, donc c'est lui
// qu'on teste. L'abonnement à `history` vit dans `useChemin.ts`, réduit à de la plomberie.

import type { Role } from '../shared/stores/sessionRoleStore'

// Les cinq « mondes » adressables. `accueil` est l'écran de choix des quatre portes (E00US017).
export type Monde = 'accueil' | 'public' | 'scoreur' | 'tablette' | 'admin'

// Une route = un monde, plus ce qui suit dans le chemin. Le routeur **ignore délibérément** la
// structure interne de l'admin (axe, destination) : il ne connaît que des segments. C'est la coquille
// admin qui sait ce qu'ils veulent dire — sans quoi le routeur deviendrait dépendant d'elle, et
// chaque nouvelle destination le ferait changer.
export interface Route {
  monde: Monde
  segments: readonly string[]
}

// Le segment d'URL de chaque monde. **`cible`, pas `tablette`** : l'adresse est lue par un bénévole
// sur l'étiquette collée devant la cible, elle doit donc parler **FFTA** (règle 3) ; `tablette` est le
// nom du *rôle de l'appareil* côté code. Les deux mots désignent la même porte, à deux publics.
const SEGMENT_PAR_MONDE: Record<Exclude<Monde, 'accueil'>, string> = {
  public: 'public',
  scoreur: 'scoreur',
  tablette: 'cible',
  admin: 'admin',
}

const MONDE_PAR_SEGMENT: Record<string, Monde> = {
  public: 'public',
  scoreur: 'scoreur',
  cible: 'tablette',
  admin: 'admin',
}

/** Découpe un chemin en segments non vides (`/admin//pilotage/` → `['admin', 'pilotage']`). */
function decouper(chemin: string): string[] {
  return chemin.split('/').filter((s) => s !== '')
}

/**
 * Traduit un chemin d'URL en route.
 *
 * Un chemin **inconnu** retombe sur l'accueil plutôt que d'afficher une page d'erreur : sur un réseau
 * de gymnase, un bénévole qui tape mal une adresse doit voir les quatre portes, pas un cul-de-sac.
 */
export function analyserChemin(chemin: string): Route {
  const [tete, ...reste] = decouper(chemin)
  if (tete === undefined) return { monde: 'accueil', segments: [] }
  const monde = MONDE_PAR_SEGMENT[tete]
  if (monde === undefined) return { monde: 'accueil', segments: [] }
  return { monde, segments: reste }
}

/** Construit le chemin d'une route. Réciproque exacte d'`analyserChemin` sur les chemins connus. */
export function construireChemin(route: Route): string {
  if (route.monde === 'accueil') return '/'
  return ['', SEGMENT_PAR_MONDE[route.monde], ...route.segments].join('/')
}

// Correspondance monde ↔ rôle. Elle est **totale dans les deux sens** sauf pour `accueil`, qui n'est
// pas un rôle mais l'absence de choix — d'où le `null`.
export function roleDuMonde(monde: Monde): Role | null {
  return monde === 'accueil' ? null : monde
}

export function mondeDuRole(role: Role): Exclude<Monde, 'accueil'> {
  return role
}
