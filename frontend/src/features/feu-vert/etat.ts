// Logique de présentation **pure** du feu vert (E12US002) — testée sans rendu (norme du repo :
// la décision d'affichage vit ici, `FeuVert.tsx` ne fait qu'assembler). Aucune dépendance React.

import type { DuelAVenir, Duelliste, ResumeLancement } from './api'

export type ClasseEtat = 'pret' | 'attente'

// L'état visuel d'un duel : **prêt** (vert `--success`) ou **en attente** (ambre `--danger`, jamais rouge
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

// Un archer qu'on peut déclarer forfait pour lever le blocage : son duel amont l'accompagne, car
// c'est là que le forfait se déclare (E16US008).
export interface ArcherForfaitable {
  archer_id: number
  libelle: string
  numero_duel: number
}

// Un duel amont **déplié sur la ligne bloquée** : de quoi aller chercher les tireurs sans quitter
// l'écran, et de quoi viser le forfait.
export interface DuelSource {
  numero: number
  detail: string
  archers: ArcherForfaitable[]
}

// L'action qui lève le manquement d'une ligne (`null` = rien ne le lève depuis cet écran).
export type ActionLigne =
  | { genre: 'sources'; sources: DuelSource[] }
  | { genre: 'placement' }
  | { genre: 'sans-recours'; explication: string }

// ⚠️ Le placement des cibles n'existe qu'au **tour 1** (`ServicePilotageTour._duel_a_venir`,
// `DETTE-019`) : au-delà, « cible non attribuée » ne se lève par aucun geste, et un lien vers le
// plan de cibles serait une fausse porte. On dit la limite plutôt que de l'offrir.
const SANS_RECOURS_HORS_TOUR_1 =
  'Les cibles ne sont posées qu’au premier tour : ce duel ne peut pas encore partir d’ici.'

export function actionDuel(duel: DuelAVenir, duels: DuelAVenir[]): ActionLigne | null {
  if (duel.pret_a_lancer) return null
  if (duel.sources_en_attente.length > 0) {
    return { genre: 'sources', sources: duel.sources_en_attente.map((n) => deplier(n, duels)) }
  }
  // « adversaire non déterminé » (aucune source) se répare à la composition de la phase, pas ici.
  if (!duel.participants_connus) return null
  if (duel.cible_attribuee) return null
  if (duel.tour > 1) return { genre: 'sans-recours', explication: SANS_RECOURS_HORS_TOUR_1 }
  return { genre: 'placement' }
}

// Le duel amont tel qu'il se lit sur la ligne bloquée. Il peut avoir quitté la liste entre deux
// poll (5 s) : on le nomme quand même, sans rien à forfaire.
function deplier(numero: number, duels: DuelAVenir[]): DuelSource {
  const source = duels.find((d) => d.numero === numero)
  if (source === undefined) {
    return { numero, detail: 'plus dans la liste des duels à venir', archers: [] }
  }
  // ⚠️ Deux décisions distinctes, à ne pas confondre. Le FORFAIT exige les deux camps :
  // `ServiceSaisieDuels._appliquer_forfaits` saute un match dont un camp est vide, un forfait posé
  // là s'écrirait sans rien débloquer. Le DÉPLIAGE, lui, doit dire ce qu'il sait — le CA veut
  // « ses occupants, sa cible », et le camp connu est justement l'archer à aller chercher.
  if (source.haut === null && source.bas === null) {
    return { numero, detail: 'occupants pas encore connus', archers: [] }
  }
  if (source.haut === null || source.bas === null) {
    const cibleUnique = libelleCibles(source)
    const connus = `${nomDuelliste(source.haut)} vs ${nomDuelliste(source.bas)}`
    return {
      numero,
      detail: cibleUnique ? `${connus} · ${cibleUnique}` : connus,
      archers: [],
    }
  }
  const archers = [source.haut, source.bas].map((d) => ({
    archer_id: d.archer_id,
    libelle: nomDuelliste(d),
    numero_duel: numero,
  }))
  const cibles = libelleCibles(source)
  const opposants = `${nomDuelliste(source.haut)} vs ${nomDuelliste(source.bas)}`
  return { numero, detail: cibles ? `${opposants} · ${cibles}` : opposants, archers }
}

export function archersForfaitables(sources: DuelSource[]): ArcherForfaitable[] {
  return sources.flatMap((source) => source.archers)
}
