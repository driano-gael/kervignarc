// Manipulation d'une **séquence d'étapes** de format (E01US024) — logique pure, aucun React.
//
// Deux gestes, et le second est ce qui les rend sûrs : réordonner ou retirer une étape **renumérote
// les ordres**, or `ordre_source` désigne une phase **par son ordre** (`# DETTE-026`) — sans
// remappage, monter une phase d'un cran fait glisser en silence les prélèvements de ses cadettes.
// Le backend fait déjà exactement cela (`_remapper`) et **refuse** de retirer une phase encore
// référencée : c'est la parité avec l'écran équivalent qui manquait, pas une subtilité nouvelle.

import type { Etape, Source } from '../patrimoine/api'
import { decrireProfondeur } from '../../shared/phases/profondeur'
import { deplacer } from '../phases/ordre'

/** Ordre sentinelle d'un prélèvement **orphelin** — hors de toute séquence, donc introuvable.
 *
 * ⚠️ La valeur importe : il faut qu'aucune étape ne la porte **et** qu'elle soit supérieure à
 * toutes les autres, pour que le diagnostic rende `source_phase_introuvable` (le défaut réel) et
 * non `source_apres_phase` (un défaut d'ordre, qui égarerait l'organisateur). `renumeroter` la
 * recalcule à partir de la longueur de la séquence. */
function ordreOrphelin(taille: number): number {
  return taille + 1
}

/** Renumérote les ordres selon la **position** et remappe les prélèvements en conséquence.
 *
 * Le remappage préserve l'**intention** : « je prélève dans la phase qui était la 2ᵉ » reste vrai
 * quand elle devient la 3ᵉ. ⚠️ **Un prélèvement dont l'étape a disparu est rendu explicitement
 * introuvable** : le laisser tel quel était pire que le trou qu'on fermait — tous les ordres étant
 * renumérotés, la valeur conservée désigne **la phase qui suivait celle qu'on retire**, ce qui
 * faisait puiser la finale dans le mauvais tableau **sans aucune anomalie**.
 */
export function renumeroter(etapes: readonly Etape[]): Etape[] {
  const ancienVersNouveau = new Map<number, number>()
  etapes.forEach((etape, index) => ancienVersNouveau.set(etape.ordre, index + 1))
  const orphelin = ordreOrphelin(etapes.length)
  return etapes.map((etape, index) => ({
    ...etape,
    ordre: index + 1,
    sources: etape.sources.map((source) => remapper(source, ancienVersNouveau, orphelin)),
  }))
}

function remapper(
  source: Source,
  ancienVersNouveau: ReadonlyMap<number, number>,
  orphelin: number,
): Source {
  const cible = ancienVersNouveau.get(source.ordre_source)
  return { ...source, ordre_source: cible ?? orphelin }
}

/** Déplace l'étape d'index `de` vers `vers`, puis renumérote et remappe. */
export function deplacerEtape(etapes: readonly Etape[], de: number, vers: number): Etape[] {
  return renumeroter(deplacer(etapes, de, vers))
}

/** Retire l'étape d'index `index`, puis renumérote et remappe. */
export function retirerEtape(etapes: readonly Etape[], index: number): Etape[] {
  return renumeroter(etapes.filter((_, position) => position !== index))
}

/** Ajoute une étape en fin de séquence (son ordre est dérivé de sa position). */
export function ajouterEtape(etapes: readonly Etape[], etape: Etape): Etape[] {
  return renumeroter([...etapes, etape])
}

/** Remplace l'étape d'index `index`, puis renumérote et remappe. */
export function remplacerEtape(etapes: readonly Etape[], index: number, etape: Etape): Etape[] {
  return renumeroter(etapes.map((existante, position) => (position === index ? etape : existante)))
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
  // La profondeur n'apparaît que si elle est **réglée** : une phase au preset se lit comme avant,
  // et afficher « podium » partout ferait passer un défaut hérité pour une décision (E06US006).
  if (etape.profondeur !== null) morceaux.push(decrireProfondeur(etape.profondeur))
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
export { decrireProfondeur }

export function lireEntier(saisi: string): number | null | undefined {
  if (saisi.trim() === '') return null
  const valeur = Number(saisi)
  return Number.isInteger(valeur) && valeur >= 1 ? valeur : undefined
}
