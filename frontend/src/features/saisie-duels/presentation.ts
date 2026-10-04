// Libellés de l'écran de saisie en duels (E04US013) : ce que le scoreur lit, calculé hors du rendu.
// Séparé du `.tsx` pour être testé sous `node` ; les décisions de saisie vivent dans `duel.ts`.

import { libelleEcartCourt } from '../equipes/presentation'
import type { Camp, Cote, Duel, EquipeEcartee } from './api'
import { libelleMode, type StatutDuel } from './duel'

const LIBELLE_STATUT: Record<StatutDuel, string> = {
  bye: 'Exempt (bye)',
  attente_adversaires: 'En attente des adversaires',
  a_saisir: 'À saisir',
  en_cours: 'En cours',
  a_valider: 'À valider',
  valide: 'Validé',
}

export function libelleStatut(statut: StatutDuel): string {
  return LIBELLE_STATUT[statut]
}

// Un camp d'équipe se nomme par l'équipe et ses membres (E13US004) ; un archer, « nom prénom ».
// Un camp encore inconnu s'affiche « — ».
export function nomCamp(camp: Camp | null): string {
  if (camp === null) return '—'
  if (camp.archer_id !== null) return `${camp.nom} ${camp.prenom}`
  return camp.membres && camp.membres.length > 0
    ? `${camp.nom} (${camp.membres.join(', ')})`
    : camp.nom
}

// Le nom court d'un camp sur le pavé (volées, barrage, vainqueur) : son `nom` seul, ou le côté.
export function nomCourt(camp: Camp | null, cote: Cote): string {
  if (camp !== null) return camp.nom
  return cote === 'haut' ? 'Haut' : 'Bas'
}

export function nomVainqueur(duel: Pick<Duel, 'haut' | 'bas' | 'resultat'>): string | null {
  const vainqueur = duel.resultat?.vainqueur
  if (vainqueur === 'haut') return nomCourt(duel.haut, 'haut')
  if (vainqueur === 'bas') return nomCourt(duel.bas, 'bas')
  return null
}

// Les motifs qui écartent une équipe du tableau : ses écarts de conformité, puis ses membres hors course.
export function motifsEcart(equipe: EquipeEcartee): string {
  return [
    ...equipe.ecarts.map(libelleEcartCourt),
    ...equipe.membres_hors_course.map(
      (membre) => `${membre} n’est pas en lice dans ce départ (absent, forfait ou disqualifié)`,
    ),
  ].join(' ; ')
}

// La ligne de méta d'un duel : mode, seuil de victoire en sets, et l'annotation hors-ligne.
export function libelleMetaDuel(
  duel: Pick<Duel, 'mode' | 'points_pour_gagner' | 'en_attente'>,
): string {
  const seuil =
    duel.mode === 'sets' && duel.points_pour_gagner !== null
      ? ` — premier à ${duel.points_pour_gagner} points`
      : ''
  const attente = duel.en_attente === true ? ' · en attente d’envoi' : ''
  return `${libelleMode(duel.mode)}${seuil}${attente}`
}

export function titreBarrage(nbFleches: number): string {
  return nbFleches === 1
    ? 'Barrage (une flèche par archer, le plus près du centre)'
    : `Barrage (${nbFleches} flèches par camp : le plus haut total, puis le plus près du centre)`
}

// Le bandeau de la file hors-ligne des duels : rien à dire quand elle est vide.
export function libelleSaisiesEnAttente(enAttente: number): string | null {
  if (enAttente === 0) return null
  return `${enAttente} saisie${enAttente > 1 ? 's' : ''} en attente d’envoi`
}
