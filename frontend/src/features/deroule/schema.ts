// Mise en page du **schéma à braquets** (E01US024) — géométrie pure, aucun React, aucun DOM.
//
// Convention du projet : le JSX ne se teste pas, la logique si (`features/blasons/zones.ts`,
// `features/phases/ordre.ts`). Tout ce qui se calcule — positions, tailles, tracés des flèches —
// vit donc ici, et `Deroule.tsx` ne fait que rendre le `Plan` obtenu.
//
// **SVG maison, aucune bibliothèque** (règle 11 ; précédent DETTE-024, routeur maison). Un graphe
// de 3 à 8 nœuds en colonnes ne justifie pas une dépendance de layout : la disposition est linéaire
// (une colonne par phase, dans l'ordre), et les seules courbes sont les flèches qui sautent
// par-dessus une ou plusieurs colonnes.

import type { Bloc, Flux } from './api'

export const LARGEUR_BLOC = 190
export const ESPACE_COLONNE = 74
/** Hauteur d'un bloc sans braquets ; chaque tour affiché en ajoute `HAUTEUR_TOUR`. */
export const HAUTEUR_BASE = 132
export const HAUTEUR_TOUR = 18
export const MARGE = 16
/** Réserve sous les blocs pour les flèches qui sautent une colonne ou plus. */
export const COULOIR_SAUT = 56

export interface Noeud {
  ordre: number
  x: number
  y: number
  largeur: number
  hauteur: number
}

export interface Arete {
  /** Clé de rendu React, stable : deux prélèvements d'une même paire de phases se distinguent. */
  cle: string
  ordre_source: number
  ordre_cible: number
  /** Tracé SVG (`d`) : segment droit entre colonnes voisines, courbe sous les blocs sinon. */
  trace: string
  /** Où poser l'étiquette de la flèche (« rangs 33→120 », « gagnants du tour 2 »). */
  etiquette_x: number
  etiquette_y: number
  effectif: number | null
  saute: boolean
}

export interface Plan {
  largeur: number
  hauteur: number
  noeuds: Noeud[]
  aretes: Arete[]
}

/** La hauteur d'un bloc : de quoi loger ses braquets sans les tronquer. */
export function hauteurBloc(bloc: Bloc): number {
  return HAUTEUR_BASE + bloc.tours.length * HAUTEUR_TOUR
}

/**
 * Dispose les blocs en colonnes (une par phase, dans l'ordre) et trace une flèche par prélèvement.
 *
 * Les blocs sont alignés **en haut** plutôt que centrés : leurs hauteurs varient avec le nombre de
 * braquets, et un alignement centré ferait danser les points d'attache des flèches d'un effectif à
 * l'autre — le dessin bougerait sans que le format ait changé.
 */
export function disposer(blocs: readonly Bloc[]): Plan {
  const ordonnes = [...blocs].sort((a, b) => a.ordre - b.ordre)
  const colonnes = new Map<number, number>()
  const noeuds: Noeud[] = ordonnes.map((bloc, index) => {
    colonnes.set(bloc.ordre, index)
    return {
      ordre: bloc.ordre,
      x: MARGE + index * (LARGEUR_BLOC + ESPACE_COLONNE),
      y: MARGE,
      largeur: LARGEUR_BLOC,
      hauteur: hauteurBloc(bloc),
    }
  })

  const hauteurMax = noeuds.reduce((max, noeud) => Math.max(max, noeud.hauteur), 0)
  const aretes: Arete[] = []
  ordonnes.forEach((bloc) => {
    bloc.entrees.forEach((flux, rang) => {
      const arete = tracer(flux, rang, noeuds, colonnes, hauteurMax)
      if (arete !== null) aretes.push(arete)
    })
  })

  return {
    largeur:
      noeuds.length === 0
        ? 0
        : MARGE * 2 + noeuds.length * LARGEUR_BLOC + (noeuds.length - 1) * ESPACE_COLONNE,
    hauteur: MARGE * 2 + hauteurMax + (aretes.some((a) => a.saute) ? COULOIR_SAUT : 0),
    noeuds,
    aretes,
  }
}

/**
 * Trace une flèche du bord droit de sa source au bord gauche de sa cible.
 *
 * Entre colonnes **voisines**, un segment droit suffit. Dès qu'elle en saute une, la flèche
 * passerait **à travers** les blocs intermédiaires : elle est alors renvoyée sous eux par une
 * courbe quadratique. Rend `null` si la source n'est pas dans le plan — cas d'un format incohérent
 * (source introuvable, source postérieure), que le diagnostic signale déjà comme bloquant : mieux
 * vaut ne pas dessiner de flèche que d'en dessiner une qui ne mène nulle part.
 */
function tracer(
  flux: Flux,
  rang: number,
  noeuds: readonly Noeud[],
  colonnes: ReadonlyMap<number, number>,
  hauteurMax: number,
): Arete | null {
  const indexSource = colonnes.get(flux.ordre_source)
  const indexCible = colonnes.get(flux.ordre_cible)
  if (indexSource === undefined || indexCible === undefined) return null
  const source = noeuds[indexSource]
  const cible = noeuds[indexCible]
  if (source === undefined || cible === undefined) return null

  const cle = `${flux.ordre_source}-${flux.ordre_cible}-${rang}`
  const saute = Math.abs(indexCible - indexSource) > 1
  // Les prélèvements multiples d'un même bloc s'étagent verticalement pour ne pas se superposer.
  const decalage = rang * 14
  const yDepart = source.y + 46 + decalage
  const yArrivee = cible.y + 46 + decalage
  const xDepart = source.x + source.largeur
  const xArrivee = cible.x

  if (!saute) {
    return {
      cle,
      ordre_source: flux.ordre_source,
      ordre_cible: flux.ordre_cible,
      trace: `M ${xDepart} ${yDepart} L ${xArrivee} ${yArrivee}`,
      etiquette_x: (xDepart + xArrivee) / 2,
      etiquette_y: (yDepart + yArrivee) / 2 - 6,
      effectif: flux.effectif,
      saute,
    }
  }

  const creux = MARGE + hauteurMax + COULOIR_SAUT - 12 + decalage
  const milieu = (xDepart + xArrivee) / 2
  return {
    cle,
    ordre_source: flux.ordre_source,
    ordre_cible: flux.ordre_cible,
    trace: `M ${xDepart} ${yDepart} Q ${milieu} ${creux} ${xArrivee} ${yArrivee}`,
    etiquette_x: milieu,
    // Sur une quadratique, l'ordonnée au paramètre 0,5 vaut (départ + 2×contrôle + arrivée) / 4 :
    // poser l'étiquette au creux la décollerait de la courbe.
    etiquette_y: (yDepart + 2 * creux + yArrivee) / 4 - 6,
    effectif: flux.effectif,
    saute,
  }
}
