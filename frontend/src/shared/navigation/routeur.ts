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

import type { Role } from '../stores/sessionRoleStore'

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
  // `salle` **est** le monde tablette : un écran de projection est un *poste*, rattaché par le même
  // code et le même jeton (cf. `Porte` ci-dessous). Deux adresses, une mécanique.
  salle: 'tablette',
  admin: 'admin',
}

// ————————————————————————————————————————————————————————————————————————————————————————————————
// Portes — ce que l'utilisateur franchit, à distinguer du monde que l'app sert
// ————————————————————————————————————————————————————————————————————————————————————————————————
//
// Retour maquettes du 04/08/2026 (A00, « ce qui manque complètement ») : *« une porte pour le ou les
// écrans de projections »*. Elle **n'ajoute pas un monde** : un écran de salle est un poste, avec le
// même code de rattachement, le même jeton, le même heartbeat et la même révocation — c'est le `type`
// rendu par le serveur qui aiguille ensuite vers la saisie ou l'affichage plein écran (cf. l'en-tête
// d'`EspacePoste`, qui a déjà tranché ce point en E07US004).
//
// Ce qui manquait n'était donc pas de la mécanique mais de **l'orientation** : rien, à l'écran de
// choix, ne disait au bénévole que le vidéoprojecteur passe par là — il devait franchir « Tablette de
// cible » pour rattacher un écran, ce qui est faux dans les mots. D'où une **porte** de plus,
// c'est-à-dire une adresse (`/salle`) et un intitulé, pour un monde inchangé.
//
// ⚠️ **Asymétrie assumée** : `porte → chemin` est total, `chemin → monde` écrase la distinction
// (`/salle` et `/cible` donnent tous deux `tablette`). `construireChemin({ monde: 'tablette' })`
// rend donc toujours `/cible`. Sans conséquence : l'app ne *reconstruit* jamais cette adresse pour
// un poste déjà installé (`mondeAServir` ne corrige que depuis la racine), et un écran laissé sur
// `/salle` y reste — c'est justement ce qu'on veut d'une machine allumée huit heures.
export type Porte = Role | 'salle'

const SEGMENT_PAR_PORTE: Record<Porte, string> = {
  public: 'public',
  scoreur: 'scoreur',
  tablette: 'cible',
  salle: 'salle',
  admin: 'admin',
}

/** L'adresse d'une porte — ce vers quoi navigue un tap à l'écran de choix. */
export function cheminDePorte(porte: Porte): string {
  return `/${SEGMENT_PAR_PORTE[porte]}`
}

/** Le rôle d'appareil derrière une porte. Deux portes, un rôle : `salle` est un poste. */
export function roleDeLaPorte(porte: Porte): Role {
  return porte === 'salle' ? 'tablette' : porte
}

/**
 * La porte que **l'adresse** nomme, ou `null` si l'adresse n'en nomme aucune.
 *
 * C'est ce qui permet à l'écran de rattachement de parler juste (« rattacher cet écran de salle »
 * plutôt que « cette tablette ») **sans stocker de préférence** : l'adresse porte déjà l'information
 * et survit au rechargement. Un état local de plus n'aurait fait que diverger d'elle.
 */
export function porteDuChemin(chemin: string): Porte | null {
  const [tete] = decouper(chemin)
  if (tete === undefined) return null
  const entree = Object.entries(SEGMENT_PAR_PORTE).find(([, segment]) => segment === tete)
  return entree === undefined ? null : (entree[0] as Porte)
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
