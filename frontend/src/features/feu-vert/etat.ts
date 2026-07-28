// Logique de présentation **pure** du feu vert (E12US002) — testée sans rendu (norme du repo :
// la décision d'affichage vit ici, `FeuVert.tsx` ne fait qu'assembler). Aucune dépendance React.

import type { DuelAVenir, Duelliste, ResumeLancement } from './api'

export type ClasseEtat = 'pret' | 'attente'

// L'état visuel d'un duel : **prêt** (vert `--ok`) ou **en attente** (ambre `--warn`, jamais rouge
// sur fond sombre — DV-03). Le libellé nomme ce qui bloque (le CA : « pas seulement signalé »).
export function afficheDuel(duel: DuelAVenir): { classe: ClasseEtat; libelle: string } {
  if (duel.pret_a_lancer) return { classe: 'pret', libelle: 'Prêt' }
  return { classe: 'attente', libelle: duel.blocage ?? 'En attente' }
}

// Le nom d'un duelliste pour l'affichage, ou « — » si le camp n'a pas encore d'occupant.
export function nomDuelliste(duelliste: Duelliste | null): string {
  if (duelliste === null) return '—'
  return `${duelliste.prenom} ${duelliste.nom}`
}

// La (ou les) cible(s) d'un duel prêt, pour l'afficher sur sa ligne (« cible 4 », « cibles 4 et 7 »).
export function libelleCibles(duel: DuelAVenir): string {
  const cibles = [duel.cible_haut, duel.cible_bas].filter((c): c is number => c !== null)
  const distinctes = [...new Set(cibles)].sort((a, b) => a - b)
  if (distinctes.length === 0) return ''
  if (distinctes.length === 1) return `cible ${distinctes[0]}`
  return `cibles ${distinctes.join(' et ')}`
}

// Le libellé **chiffré** du bouton de lancement (CA : « le bouton chiffre ce qu'il déclenche »).
// `null` si rien n'est prêt (le bouton est alors désactivé, pas de chiffre à montrer).
export function libelleBouton(impact: ResumeLancement): string | null {
  if (impact.nb_duels === 0) return null
  const cibles = impact.cibles.length > 0 ? ` · cibles ${impact.cibles.join(', ')}` : ''
  const duels = impact.nb_duels === 1 ? '1 duel' : `${impact.nb_duels} duels`
  return `Lancer — ${duels}${cibles} · ${impact.nb_archers} archers prévenus`
}
