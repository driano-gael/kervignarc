// Durée prévue et heure prévue d'une étape (E03US010, ADR-0118). Le calcul des heures vit au
// serveur (`domain/horaire_prevu.py`) : ce module ne fait que lire et écrire, jamais calculer.

/** Miroir de `DUREE_PREVUE_MAX` (domaine) : borne de saisie, le refus réel reste au serveur. */
export const DUREE_PREVUE_MAX = 1440

/** Le texte du champ vers la valeur envoyée : vide = durée inconnue. */
export function versDureePrevue(texte: string): number | null {
  const nettoye = texte.trim()
  return nettoye === '' ? null : Number(nettoye)
}

export function depuisDureePrevue(duree: number | null): string {
  return duree === null ? '' : String(duree)
}

/** « 1 h 30 », « 45 min » — la durée telle qu'un organisateur la dit. */
export function decrireDuree(minutes: number): string {
  const heures = Math.floor(minutes / 60)
  const reste = minutes % 60
  if (heures === 0) return `${reste} min`
  return reste === 0 ? `${heures} h` : `${heures} h ${String(reste).padStart(2, '0')}`
}

/** « 09:30 », « 00:30 (lendemain) » ; « — » pour une heure inconnue (CA 3 et 5). */
export function decrireHeure(heure: { heure: string; jours_apres: number } | null): string {
  if (heure === null) return '—'
  if (heure.jours_apres === 0) return heure.heure
  if (heure.jours_apres === 1) return `${heure.heure} (lendemain)`
  return `${heure.heure} (J+${heure.jours_apres})`
}
