// Logique **pure** de réordonnancement de la séquence de phases (E05US001), extraite du composant
// pour être testable en isolation (convention front : le JSX n'est pas testé, la logique l'est —
// cf. `placement/planConsultation.ts`). Le geste UI (boutons monter/descendre) délègue ici, puis
// envoie la liste d'identifiants obtenue à l'API `reordonner`.

export type Direction = 'monter' | 'descendre'

/** Ce qu'il faut savoir d'une étape pour la déplacer : rien d'autre que son identité.
 *
 * Structural plutôt qu'`EtapeDeroule` : cette logique ne lit ni type, ni barème, ni statut, et
 * l'ancrer au DTO complet l'aurait fait suivre chaque évolution de la frontière API — la
 * réécriture qu'ADR-0076 vient d'imposer à ce fichier en est la démonstration. */
export interface Deplacable {
  id: number
}

// Déplace l'élément d'index `de` vers l'index `vers` (immuable). Hors bornes → liste inchangée.
export function deplacer<T>(liste: readonly T[], de: number, vers: number): T[] {
  if (de < 0 || de >= liste.length || vers < 0 || vers >= liste.length) return [...liste]
  const copie = [...liste]
  const [element] = copie.splice(de, 1)
  // `de` est dans les bornes, donc `element` existe ; le garde lève le `T | undefined` de l'accès
  // indexé (noUncheckedIndexedAccess) sans changer le comportement.
  if (element === undefined) return [...liste]
  copie.splice(vers, 0, element)
  return copie
}

// Renvoie la liste des identifiants **dans le nouvel ordre** après avoir monté ou descendu
// l'étape `phaseId` d'un cran. Si le mouvement est impossible (déjà en tête / en queue, ou étape
// absente), renvoie `null` — l'appelant n'émet alors aucune requête.
export function ordreApresDeplacement(
  phases: readonly Deplacable[],
  phaseId: number,
  direction: Direction,
): number[] | null {
  const index = phases.findIndex((phase) => phase.id === phaseId)
  if (index === -1) return null
  const cible = direction === 'monter' ? index - 1 : index + 1
  if (cible < 0 || cible >= phases.length) return null
  return deplacer(phases, index, cible).map((phase) => phase.id)
}
