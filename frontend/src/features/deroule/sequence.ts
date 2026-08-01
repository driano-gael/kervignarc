// Manipulation d'une **séquence d'étapes** de format (E01US024) — logique pure, aucun React.
//
// Deux gestes, et le second est ce qui les rend sûrs : réordonner ou retirer une étape **renumérote
// les ordres**, or `ordre_source` désigne une phase **par son ordre** (`# DETTE-026`). Sans
// remappage, monter une phase d'un cran fait glisser en silence les prélèvements de ses cadettes
// sur la voisine.
//
// Le backend fait déjà exactement cela pour les phases d'un tournoi — `ServicePhases.reordonner`
// remappe (`_remapper`) et `supprimer` **refuse** de retirer une phase encore référencée
// (`PhaseSourceReferencee`). Un premier jet de cet écran ne faisait ni l'un ni l'autre : c'est la
// parité avec l'écran équivalent qui manquait, pas une subtilité nouvelle.

import type { Etape, Source } from '../patrimoine/api'
import { deplacer } from '../phases/ordre'

/**
 * Renumérote les ordres selon la **position** et remappe les prélèvements en conséquence.
 *
 * Les ordres sont dérivés de la position, jamais saisis — ce qui supprime par construction la
 * classe d'erreurs « ordres non contigus ». Le remappage préserve l'**intention** : « je prélève
 * dans la phase qui était la 2ᵉ » reste vrai après que cette phase soit devenue la 3ᵉ.
 *
 * Un prélèvement qui désignait une étape **disparue** est laissé tel quel plutôt que réaffecté à
 * une voisine : le diagnostic le signalera en `source_phase_introuvable`, ce qui est visible et
 * corrigible. Le glisser sur la phase d'à côté serait faux **et** silencieux.
 */
export function renumeroter(etapes: readonly Etape[], avant: readonly Etape[]): Etape[] {
  const ancienVersNouveau = new Map<number, number>()
  etapes.forEach((etape, index) => ancienVersNouveau.set(etape.ordre, index + 1))
  const survivants = new Set(etapes.map((etape) => etape.ordre))
  // Les ordres disparus (étape retirée) ne sont pas remappés : on les laisse pointer dans le vide.
  avant.forEach((etape) => {
    if (!survivants.has(etape.ordre)) ancienVersNouveau.delete(etape.ordre)
  })
  return etapes.map((etape, index) => ({
    ...etape,
    ordre: index + 1,
    sources: etape.sources.map((source) => remapper(source, ancienVersNouveau)),
  }))
}

function remapper(source: Source, ancienVersNouveau: ReadonlyMap<number, number>): Source {
  const cible = ancienVersNouveau.get(source.ordre_source)
  return cible === undefined ? source : { ...source, ordre_source: cible }
}

/** Déplace l'étape d'index `de` vers `vers`, puis renumérote et remappe. */
export function deplacerEtape(etapes: readonly Etape[], de: number, vers: number): Etape[] {
  return renumeroter(deplacer(etapes, de, vers), etapes)
}

/** Retire l'étape d'index `index`, puis renumérote et remappe. */
export function retirerEtape(etapes: readonly Etape[], index: number): Etape[] {
  return renumeroter(
    etapes.filter((_, position) => position !== index),
    etapes,
  )
}

/** Ajoute une étape en fin de séquence (son ordre est dérivé de sa position). */
export function ajouterEtape(etapes: readonly Etape[], etape: Etape): Etape[] {
  return renumeroter([...etapes, etape], etapes)
}

/** Remplace l'étape d'index `index`, puis renumérote et remappe. */
export function remplacerEtape(etapes: readonly Etape[], index: number, etape: Etape): Etape[] {
  return renumeroter(
    etapes.map((existante, position) => (position === index ? etape : existante)),
    etapes,
  )
}

/** Décrit un prélèvement en langage d'organisateur (« rangs 1 à 32 de la phase 1 »). */
export function decrireSource(source: Source): string {
  if (source.nature === 'reste') return `le reste de la phase ${source.ordre_source}`
  if (source.nature === 'issue_de_tour') {
    return `${source.issue ?? '?'} du tour ${source.tour ?? '?'} de la phase ${source.ordre_source}`
  }
  const fin = source.rang_fin === null ? 'et suivants' : `à ${source.rang_fin}`
  return `rangs ${source.rang_debut} ${fin} de la phase ${source.ordre_source}`
}

/** Décrit une étape en une ligne, pour la liste de composition. */
export function decrireEtape(etape: Etape): string {
  const morceaux: string[] = []
  if (etape.bareme !== null) {
    morceaux.push(`${etape.bareme.nb_volees}×${etape.bareme.nb_fleches_par_volee}`)
  }
  if (etape.effectif !== null) morceaux.push(`${etape.effectif} archers`)
  morceaux.push(
    etape.sources.length === 0 ? 'tous les inscrits' : etape.sources.map(decrireSource).join(' + '),
  )
  return morceaux.join(' · ')
}

/**
 * Lit un entier saisi ; rend `null` pour « non renseigné » et `undefined` pour « invalide ».
 *
 * Les trois cas doivent se distinguer : `Number('')` vaut `0` et `Number('abc')` vaut `NaN`, que
 * `JSON.stringify` sérialise en `null` — un effectif déclaré s'effaçait donc silencieusement à la
 * moindre faute de frappe, et un barème vide partait en `0 volées` pour revenir en 422 illisible.
 */
export function lireEntier(saisi: string): number | null | undefined {
  if (saisi.trim() === '') return null
  const valeur = Number(saisi)
  return Number.isInteger(valeur) && valeur >= 1 ? valeur : undefined
}
