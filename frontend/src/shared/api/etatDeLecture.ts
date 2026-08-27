// Ce qu'une vue publique **dit** pendant qu'elle n'a pas encore de données — pure (E05US031).
//
// ⚠️ **Né d'un défaut relevé en revue, pas d'un souci de factorisation** : les vues publiques
// reprenaient la formule de `VueTableaux` (« si `isError`, annoncer une connexion perdue »), juste
// chez son auteur d'origine — `/tableaux/{id}` ne rend jamais de 409 — mais transportée sur trois
// routes qui, elles, en rendent. Une phase composée mais **pas encore réglée** faisait donc lire «
// Connexion momentanément perdue » à toute la salle. ⚠️ **Pas un remède structurel** : une fonction
// pure de six lignes, sans indirection ni point d'extension.

import { ErreurApi } from './client'

/** Ce qu'il faut afficher tant qu'aucune donnée n'est disponible.
 *
 * ⚠️ **L'ordre des tests compte**, et c'est l'appelant qui le tient : on n'appelle cette fonction
 * que si `data === undefined`. React Query garde le `data` de la dernière lecture réussie pendant un
 * échec ; tester l'erreur d'abord jetterait une photo encore exacte au premier clignotement réseau
 * et laisserait un écran projeté sur un message d'erreur pendant vingt secondes.
 */
export function messageDeLecture(requete: { isError: boolean; error: unknown }): string {
  if (!requete.isError) return 'Chargement…'
  // Un **refus déterministe** n'est pas une panne : le réessayer n'apporte rien, et l'annoncer
  // comme un incident réseau envoie chercher le problème là où il n'est pas.
  if (requete.error instanceof ErreurApi && requete.error.statut === 409) {
    return 'Cette phase n’est pas encore réglée par l’organisateur.'
  }
  return 'Connexion momentanément perdue — mise à jour au retour.'
}
