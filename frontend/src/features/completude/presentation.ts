// Dérivation **pure** de l'affichage de la complétude (E12US005) — isolée du rendu React pour être
// testée en node (comme `supervision/etat.ts` ou `app/resoudreRole.ts`). Deux responsabilités : le
// rendu d'une ligne (pastille + décompte), et la **composition du message d'avertissement** avant de
// terminer — la seule action irréversible (E01US002), qui doit chiffrer ce qui reste (`P-4`).

import type { Completude, EtatSection, LigneCompletude } from './api'

export interface AfficheEtat {
  classe: EtatSection // token CSS ; l'alerte se rend en **ambre**, jamais en rouge (charte, DV-03)
  libelle: string
}

export function afficheEtat(etat: EtatSection): AfficheEtat {
  switch (etat) {
    case 'ok':
      return { classe: 'ok', libelle: 'Terminé' }
    case 'alerte':
      return { classe: 'alerte', libelle: 'À finir' }
    case 'en_attente':
      return { classe: 'en_attente', libelle: 'En attente' }
    case 'a_venir':
      return { classe: 'a_venir', libelle: 'À venir' }
  }
}

// Décompte lisible d'une ligne (« 30/30 cibles », « 144/156 »), ou `null` si la ligne n'a pas de
// décompte (phases à venir, classement) — l'état suffit alors. L'unité dépend de la clé : le domaine
// ne porte pas le mot d'affichage (il envoie `fait`/`total` bruts), le front le mappe ici.
export function detailLigne(ligne: LigneCompletude): string | null {
  if (ligne.fait === null || ligne.total === null) return null
  const unite = ligne.cle === 'qualification' ? ' cibles' : ''
  return `${ligne.fait}/${ligne.total}${unite}`
}

// Ce qui manque, ligne par ligne, en langage d'organisateur — pour l'avertissement avant *terminer*.
// On ne liste que l'**actionnable** : les lignes en alerte / en attente, jamais les phases `a_venir`
// (séquencées EPIC-05 : ce n'est pas un manque que l'organisateur peut combler aujourd'hui).
function manques(completude: Completude): string[] {
  const messages: string[] = []
  for (const ligne of [...completude.sportif, ...completude.hors_sportif]) {
    if (ligne.etat === 'ok' || ligne.etat === 'a_venir') continue
    const reste = ligne.fait !== null && ligne.total !== null ? ligne.total - ligne.fait : null
    if (ligne.cle === 'qualification') {
      messages.push(
        reste !== null && reste > 0
          ? `${reste} cible(s) de qualification ne sont pas terminées`
          : 'la qualification n’est pas terminée',
      )
    } else if (ligne.cle === 'paiements') {
      if (reste !== null && reste > 0) messages.push(`${reste} archer(s) n’ont pas réglé`)
    } else if (ligne.cle === 'classement') {
      messages.push('le classement n’est pas définitif')
    }
  }
  return messages
}

// Message de confirmation avant de terminer (`D-17`, CDC UX §8.3). Toujours l'**implication** (ce que
// « terminer » fige), précédée du **chiffrage** de ce qui reste quand le sportif n'est pas complet —
// « Terminer quand même ? ». Sportif complet : pas d'alarme, juste l'implication + la question.
export function messageConfirmationTerminer(completude: Completude): string {
  const implication =
    'Terminer figera le sportif (qualification, classement). Les paiements resteront modifiables.'
  const restes = manques(completude)
  if (completude.sportif_complet || restes.length === 0) {
    return `${implication}\n\nTerminer le tournoi ?`
  }
  return `${restes.join(' ; ')}.\n\n${implication}\n\nTerminer quand même ?`
}
