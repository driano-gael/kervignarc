// Ce qu'une vue publique **dit** pendant qu'elle n'a pas encore de données — logique pure (E05US031).
//
// ⚠️ **Ce module naît d'un défaut relevé en revue (axe adversarial), pas d'un souci de factorisation.**
// Les vues publiques reprenaient toutes la formule de `VueTableaux` : « si `isError`, annoncer une
// connexion perdue ». Le raisonnement était **juste chez son auteur d'origine** — `/tableaux/{id}`
// ne rend jamais de 409 —, et il a été transporté sur trois routes d'état de phase qui, elles, en
// rendent : `PhasePasReglee`, `PhasePasDesPoules`, `PhasePasUnBigShootOff`.
//
// Conséquence en salle : une phase de poules composée mais **pas encore réglée** faisait lire
// « Connexion momentanément perdue » à tous les spectateurs et à l'écran projeté, alors que le
// réseau allait très bien. Le bénévole qu'on appelle cherche le Wi-Fi ; le vrai geste est un champ
// à remplir à l'atelier. Et comme les hooks portent `retry: false`, le message restait affiché
// jusqu'à la prochaine invalidation temps réel.
//
// ⚠️ **Ce n'est pas un « remède structurel » au sens du CLAUDE.md**, bien que le bloc soit écrit
// cinq fois dans le dépôt : c'est une **fonction pure de six lignes**, sans indirection, sans point
// d'extension et sans interface. Le correctif du 409 imposait de toucher les trois vues neuves de
// toute façon — l'écrire une fois coûtait moins cher que trois fois. Le ralliement de `VueTableaux`
// et `VueAffectations`, lui, reste **hors périmètre** : ces deux-là ne rendent pas de 409, donc le
// geste serait cosmétique. Cf. la note du corps de commit.

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
