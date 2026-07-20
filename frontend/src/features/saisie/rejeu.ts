// Rejeu de la file de saisie hors-ligne (E04US009, ADR-0037) — logique pure, testée en node.
//
// Renvoie les saisies mises en file pendant une coupure, **dans l'ordre** (le serveur sérialise de
// toute façon les écritures — writer unique, ADR-0005). Le **zéro doublon** est garanti côté serveur
// par l'idempotence (`identifiant_saisie`, ADR-0036) : rejouer une saisie déjà passée juste avant la
// coupure ne l'enregistre pas deux fois. La fonction ne touche à aucun store : elle dit seulement
// **quoi retirer de la file** et **où s'arrêter** ; l'appelant (le hook) applique le résultat.

import { ErreurApi } from '../../shared/api/client'
import type { VoleeEnFile } from '../../shared/stores/fileHorsLigneStore'
import { estRefusDefinitif } from './horsLigne'

export interface ResultatRejeu {
  // À retirer de la file : renvoyées avec succès **ou** refusées définitivement par le serveur.
  traitees: VoleeEnFile[]
  // Sous-ensemble des `traitees` refusé par le serveur (`ErreurApi`) : à journaliser (perte visible,
  // réconciliée par la relecture de série — cf. ADR-0037, limite assumée).
  refusees: VoleeEnFile[]
  // Vrai si le rejeu s'est **arrêté** sur une panne réseau : des saisies restent en file, à retenter
  // à la prochaine reconnexion.
  interrompu: boolean
}

export async function rejouer(
  file: readonly VoleeEnFile[],
  envoyer: (corps: VoleeEnFile) => Promise<unknown>,
  // Appartenance **vivante** à la file, relue avant chaque envoi. La liste `file` est un instantané ;
  // une saisie **en ligne** concurrente (ou une ré-édition hors-ligne) a pu, entre-temps, retirer une
  // volée de la file (elle fait désormais autorité). On la **saute** alors : sans quoi le vieux corps
  // de l'instantané réécraserait la valeur neuve côté serveur (perte silencieuse). Défaut : toujours
  // présente (rejeu d'un instantané figé, comportement des tests purs).
  estEncoreEnFile: (corps: VoleeEnFile) => boolean = () => true,
): Promise<ResultatRejeu> {
  const traitees: VoleeEnFile[] = []
  const refusees: VoleeEnFile[] = []
  for (const corps of file) {
    if (!estEncoreEnFile(corps)) continue // superseded entre-temps → ni envoyée, ni « traitée »
    try {
      await envoyer(corps)
      traitees.push(corps)
    } catch (erreur) {
      // `ErreurApi` = le serveur a **répondu**. Deux cas très différents (le mélange des deux serait
      // une perte de score silencieuse, cf. ADR-0037) :
      //  - **refus définitif** (4xx métier : hors-cible, blason introuvable…) → rejouer n'y changera
      //    rien : on retire de la file et on journalise.
      //  - **transitoire** (401 serveur redémarré / jeton perdu, 409 départ perdu, 429, **5xx**
      //    saturation à la reconnexion de masse) → un rejeu ultérieur peut réussir : on **garde** en
      //    file et on s'arrête, exactement comme une panne réseau.
      if (erreur instanceof ErreurApi && !estRefusDefinitif(erreur.statut)) {
        return { traitees, refusees, interrompu: true }
      }
      if (erreur instanceof ErreurApi) {
        traitees.push(corps)
        refusees.push(corps)
        continue
      }
      // Toute autre erreur = le `fetch` a **rejeté** (panne réseau) : on est de nouveau hors-ligne,
      // on garde le reste en file et on s'arrête là.
      return { traitees, refusees, interrompu: true }
    }
  }
  return { traitees, refusees, interrompu: false }
}
