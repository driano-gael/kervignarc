// Logique pure de l'indicateur de connexion (E00US010 + E04US009).
//
// Isolée du rendu React pour être **testée** en node. L'état affiché combine deux signaux : le lien
// WebSocket (`StatutConnexion`, posé par `RealtimeClient`) et la **file de saisie hors-ligne** (des
// saisies attendent-elles d'être renvoyées, un rejeu est-il en cours ?). Le CA E04US009 veut trois
// états visibles en permanence : **connecté / hors-ligne / synchronisation en cours**.

import type { StatutConnexion } from '../stores/connexionStore'

// La classe CSS (`indicateur--<classe>`) sépare le cas « synchronisation » des trois états de lien.
export type ClasseIndicateur = StatutConnexion | 'synchronisation'

export interface EtatIndicateur {
  classe: ClasseIndicateur
  libelle: string
}

function saisiesEnAttente(nbEnAttente: number): string {
  return `${nbEnAttente} saisie${nbEnAttente > 1 ? 's' : ''} en attente`
}

// Priorité : un **rejeu en cours** prime (on est en train de renvoyer) ; sinon des saisies en attente
// signalent qu'on est hors-ligne avec du retard à rattraper ; sinon on reflète l'état du lien.
export function etatIndicateur(
  statut: StatutConnexion,
  nbEnAttente: number,
  synchronisation: boolean,
): EtatIndicateur {
  if (synchronisation) {
    return {
      classe: 'synchronisation',
      libelle: `Synchronisation… (${saisiesEnAttente(nbEnAttente)})`,
    }
  }
  if (nbEnAttente > 0) {
    return { classe: 'deconnecte', libelle: `Hors ligne · ${saisiesEnAttente(nbEnAttente)}` }
  }
  switch (statut) {
    case 'connexion':
      return { classe: 'connexion', libelle: 'Connexion…' }
    case 'connecte':
      return { classe: 'connecte', libelle: 'En ligne' }
    case 'deconnecte':
      return { classe: 'deconnecte', libelle: 'Hors ligne' }
  }
}
