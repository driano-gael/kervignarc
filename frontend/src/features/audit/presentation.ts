// Mise en forme du journal d'audit (E16US016) — fonctions **pures**, testables sans rendu.
//
// ⚠️ `LIBELLES_ACTION` est un registre **jumeau** de `ActionAuditee` (`domain/entree_audit.py`),
// et rien ne rapproche les deux listes : elles sont dans deux langages. D'où le repli de
// `libelleAction`, qui rend le slug brut plutôt qu'une case vide — une action neuve reste lisible
// en attendant sa traduction. ⚠️ Un jumeau de plus existe côté serveur (`infrastructure/tableur/
// audit.py`), pour que l'export nomme l'acte comme l'écran.

import type { EntreeAudit } from './api'

export const LIBELLES_ACTION: Record<string, string> = {
  validation: 'Validation',
  correction_score: 'Correction',
  annulation_validation: 'Annulation de validation',
  forfait: 'Forfait',
  replacement: 'Replacement',
  paiement: 'Paiement',
  lancement: 'Lancement',
  remboursement: 'Remboursement',
}

// Les actes qui **modifient** une donnée déjà validée. La maquette A18 les compte à part : ce sont
// eux qu'on cherche dans une contestation, les validations étant le bruit de fond de la journée.
const ACTIONS_CORRECTIVES = ['correction_score', 'annulation_validation']

export function libelleAction(action: string): string {
  return LIBELLES_ACTION[action] ?? action
}

export function estCorrective(entree: EntreeAudit): boolean {
  return ACTIONS_CORRECTIVES.includes(entree.action)
}

/** L'horodatage en heure **locale**, à la seconde — une trace se lit à la seconde près.
 *
 * ⚠️ Le serveur stocke et exporte en **UTC** ; l'écran, lui, affiche l'heure de la salle, la seule
 * que l'organisateur puisse recouper avec ce dont il se souvient. Les deux disent le même instant.
 */
export function heureLocale(horodatage: string): string {
  const date = new Date(horodatage)
  if (Number.isNaN(date.getTime())) return horodatage
  return date.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'medium' })
}

/** Les actions réellement présentes, pour ne proposer au filtre que ce qui existe.
 *
 * ⚠️ Proposer les huit actions du domaine ferait choisir « Remboursement » sur un journal qui n'en
 * contient aucun, et le tableau se viderait sans que rien n'explique pourquoi.
 */
export function actionsPresentes(entrees: EntreeAudit[]): string[] {
  return [...new Set(entrees.map((entree) => entree.action))].sort((a, b) =>
    libelleAction(a).localeCompare(libelleAction(b), 'fr'),
  )
}

function replier(texte: string): string {
  return texte
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLocaleLowerCase('fr')
}

/** Filtre le journal : par action, puis par recherche libre sur qui / quoi / avant-après.
 *
 * `DETTE-101` : le filtrage est **client**, sur le journal entier chargé — le serveur ne sait pas
 * filtrer. Le repli d'accents ci-dessous est ce qui rendra la résorption non triviale.
 *
 * ⚠️ La recherche replie casse et accents, **pas les espaces** : « le guén » trouve « LE GUEN »,
 * « leguen » non. Supprimer les espaces serait une autre règle, non demandée.
 */
export function filtrer(entrees: EntreeAudit[], action: string, recherche: string): EntreeAudit[] {
  const terme = replier(recherche.trim())
  return entrees.filter((entree) => {
    if (action !== '' && entree.action !== action) return false
    if (terme === '') return true
    const champs = [entree.auteur, entree.objet, entree.avant ?? '', entree.apres ?? '']
    return champs.some((champ) => replier(champ).includes(terme))
  })
}
