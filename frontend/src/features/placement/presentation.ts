// Présentation de la mixité des clubs sur les cibles (E03US006, RG-3) — logique pure, testée en
// node (comme les autres `presentation.ts` des features). Le serveur signale au niveau **cible**
// les cas où la mixité « ≥ 2 clubs par cible » n'est pas garantie (un seul club, ou club inconnu —
// *indécidable*, ADR-0014) ; ici on dérive le décompte et le résumé affichés, sans dépendre d'un
// composant. C'est un **avertissement d'équité** (ambre, DV-03), jamais une erreur : l'admin ajuste
// à la main s'il le souhaite (E03US004).

import type { CiblePlacee, Cloisonnement, RaisonConflit } from './api'

// Nombre de cibles dont la mixité de club n'est pas garantie (≥ 2 archers, < 2 clubs connus).
export function compterMixiteNonGarantie(cibles: CiblePlacee[]): number {
  return cibles.filter((cible) => cible.mixite_non_garantie).length
}

// Résumé pour la bannière de l'écran de placement : `null` quand tout va bien (pas de bannière),
// sinon un message **chiffré** au bon accord (1 cible / N cibles), sur le modèle des autres alertes
// ambre de l'écran.
export function resumeMixiteNonGarantie(cibles: CiblePlacee[]): string | null {
  const nombre = compterMixiteNonGarantie(cibles)
  if (nombre === 0) return null
  const pluriel = nombre > 1
  return `${nombre} cible${pluriel ? 's' : ''} sans mixité de club garantie (un seul club, ou club inconnu).`
}

// --- Cloisonnement des cibles (E03US007) --------------------------------------------------------

// Libellé du réglage à quatre positions, source unique du sélecteur (et de l'ordre des positions,
// dérivé plus bas) — pour que l'écran ne puisse pas dire « par catégorie » à un endroit et
// « catégories » à un autre. Ordre du plus permissif au plus strict, comme l'énumération du domaine.
//
// # DETTE-036 : la quatrième position rend aujourd'hui le **même plan** que la deuxième (le blason
// d'un archer est celui de sa catégorie). Elle est offerte quand même — choix du commanditaire —
// et se distinguera avec EF-1.4 (une phase surcharge le blason). Ne pas la retirer d'ici là : la
// remettre coûterait une migration et un réglage de club invalidé entre-temps.
export const LIBELLE_CLOISONNEMENT: Record<Cloisonnement, string> = {
  aucun: 'Aucun cloisonnement',
  categorie: 'Une seule catégorie par cible',
  blason: 'Un seul blason par cible',
  blason_et_categorie: 'Un seul blason et une seule catégorie par cible',
}

// Positions du sélecteur, **dérivées** du libellé plutôt que réécrites : une 5ᵉ valeur ajoutée à
// l'union casserait le `Record` ci-dessus, mais aurait laissé une liste écrite à la main incomplète
// sans que rien ne l'attrape — c'est exactement le mécanisme du défaut d'E03US007 côté duels.
// L'ordre des clés d'un objet littéral est celui de l'écriture : du plus permissif au plus strict.
export const VALEURS_CLOISONNEMENT = Object.keys(LIBELLE_CLOISONNEMENT) as Cloisonnement[]

// Résumé de la bannière : `null` quand aucune cible ne viole le réglage (rien à dire). Sinon un
// message **chiffré** qui dit aussi **quoi faire** — ces cibles viennent forcément d'un plan posé
// avant l'activation du réglage, et c'est la régénération qui les remet d'aplomb.
//
// Type **structurel** (le seul champ lu) : la même bannière sert le plan de cibles et le plan de
// duels, dont les cibles ne portent pas les mêmes signaux mais bien le même cloisonnement.
export function resumeCloisonnementNonRespecte(
  cibles: { cloisonnement_non_respecte: boolean }[],
): string | null {
  const nombre = cibles.filter((cible) => cible.cloisonnement_non_respecte).length
  if (nombre === 0) return null
  const pluriel = nombre > 1
  return (
    `${nombre} cible${pluriel ? 's' : ''} ne respecte${pluriel ? 'nt' : ''} pas le cloisonnement ` +
    `demandé (plan posé avant le réglage) : régénérez le plan ou déplacez les tireurs concernés.`
  )
}

// --- Réserve : pourquoi un archer n'est pas posé ------------------------------------------------
//
// Partagé par l'écran de placement **et** par celui des duels : même endpoint, même vocabulaire
// fermé. Les deux écrans en tenaient chacun une copie jusqu'à E03US007, où seule celle du placement
// a suivi l'ajout de `cloisonnement` — la réserve des duels s'affichait alors sans motif ni ambre.
// Le `Record` sur l'union rend désormais tout oubli visible au typecheck, pour les deux écrans.
export const LIBELLE_RAISON: Record<RaisonConflit, string> = {
  sans_blason: 'sans blason',
  non_place: 'aucune cible possible',
  // Dire **le réglage**, pas « aucune cible possible » : le geste correctif n'est pas le même
  // (desserrer le cloisonnement plutôt que chercher de la place).
  cloisonnement: 'exclu par le cloisonnement',
  en_reserve: 'en attente',
}

// `en_reserve` est neutre (en attente) ; les autres sont des **anomalies** à traiter (ambre, DV-03).
export const RAISON_ANOMALIE: Record<RaisonConflit, boolean> = {
  sans_blason: true,
  non_place: true,
  cloisonnement: true,
  en_reserve: false,
}

// --- Repères d'un archer sur son jeton (E16US005) ------------------------------------------------
//
// L'écran signale au niveau **cible** que la mixité n'est pas garantie ou que le cloisonnement n'est
// pas respecté — mais il ne disait pas **qui** le cause : il fallait quitter le plan pour retrouver
// le club d'un archer ou son blason. Une cible par ligne libère la largeur qu'il faut pour porter,
// sous le nom, les trois attributs **sur lesquels l'organisateur arbitre justement** : le club
// (mixité, RG-3), la catégorie et le blason (cloisonnement, RG-4).
//
// Fonction **pure**, posée ici et non dans un composant : les deux plans — cibles et duels — la
// partagent, comme ils partagent déjà `LIBELLE_RAISON` et la bannière de cloisonnement. Un second
// exemplaire est exactement ce qui a produit le défaut d'E03US007 (cf. plus haut).
export interface ReferentielsDuPlan {
  clubs: Map<number, string>
  categories: Map<number, string>
  blasons: Map<number, string>
}

// Les repères, dans l'ordre d'affichage. Liste **éventuellement vide** — jamais de trou ni de
// libellé bouche-trou :
//
//  - `archer` absent (la liste des inscrits n'est pas encore là) → aucun repère, le nom suffit ;
//  - `club_id === null` → « club inconnu », **jamais** « aucun club » : en FFTA tout licencié a un
//    club (ADR-0014), et c'est précisément ce cas que le serveur traite comme *indécidable* pour la
//    mixité. Le taire priverait l'organisateur de la cause du badge ambre qu'il a sous les yeux ;
//  - identifiant renseigné mais introuvable au référentiel (pas encore chargé, ou brique retirée du
//    tournoi) → on **omet** le repère. « Club #7 » n'apprend rien à personne et fait du bruit sur
//    quarante lignes ; le nom de l'archer, lui, reste toujours lisible.
export function reperesArcher(
  archer: { club_id: number | null; categorie_id: number } | undefined,
  blasonId: number | null,
  referentiels: ReferentielsDuPlan,
): string[] {
  if (archer === undefined) return []
  const reperes: string[] = []
  if (archer.club_id === null) reperes.push('club inconnu')
  else {
    const club = referentiels.clubs.get(archer.club_id)
    if (club !== undefined) reperes.push(club)
  }
  const categorie = referentiels.categories.get(archer.categorie_id)
  if (categorie !== undefined) reperes.push(categorie)
  if (blasonId !== null) {
    const blason = referentiels.blasons.get(blasonId)
    if (blason !== undefined) reperes.push(blason)
  }
  return reperes
}
