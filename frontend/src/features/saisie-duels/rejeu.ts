// Rejeu de la file de saisie de duel hors-ligne (E04US013, ADR-0037) — logique pure, testée en node.
//
// Renvoie les actes mis en file pendant une coupure, **dans l'ordre** (le serveur sérialise de toute
// façon les écritures — writer unique). L'ordre importe ici plus qu'en qualif : valider suppose les
// manches déjà rejouées (cf. `fileDuelsHorsLigneStore`). Le **zéro doublon** est garanti côté serveur
// par l'idempotence (`identifiant_saisie`, ADR-0036). La fonction ne touche à aucun store : elle dit
// **quoi retirer** et **où s'arrêter** ; l'appelant (le hook) applique. Jumeau de `features/saisie/
// rejeu` (2ᵉ occurrence, règle 12).

import { ErreurApi } from '../../shared/api/client'
import type { ActeDuelEnFile } from '../../shared/stores/fileDuelsHorsLigneStore'
import { estRefusDefinitif } from './horsLigne'

export interface ResultatRejeuDuels {
  // À retirer de la file : renvoyés avec succès **ou** refusés définitivement par le serveur.
  traites: ActeDuelEnFile[]
  // Sous-ensemble des `traites` refusé par le serveur (`ErreurApi` définitive) : à journaliser
  // (perte visible, réconciliée par la relecture du duel — limite assumée, ADR-0037).
  refuses: ActeDuelEnFile[]
  // Vrai si le rejeu s'est **arrêté** (panne réseau ou refus transitoire) : des actes restent en
  // file, à retenter à la prochaine reconnexion.
  interrompu: boolean
}

export async function rejouerActes(
  file: readonly ActeDuelEnFile[],
  envoyer: (acte: ActeDuelEnFile) => Promise<unknown>,
  // Appartenance **vivante** à la file, relue avant chaque envoi. La liste `file` est un instantané ;
  // une saisie **en ligne** concurrente a pu retirer un acte entre-temps (elle fait autorité). On le
  // **saute** alors — sans quoi le vieux corps réécraserait la valeur neuve (perte silencieuse).
  estEncoreEnFile: (acte: ActeDuelEnFile) => boolean = () => true,
): Promise<ResultatRejeuDuels> {
  const traites: ActeDuelEnFile[] = []
  const refuses: ActeDuelEnFile[] = []
  for (const acte of file) {
    if (!estEncoreEnFile(acte)) continue // superseded entre-temps → ni envoyé, ni « traité »
    try {
      await envoyer(acte)
      traites.push(acte)
    } catch (erreur) {
      // `ErreurApi` = le serveur a **répondu**. Refus **définitif** (4xx métier) → on retire et on
      // journalise ; **transitoire** (401/409/429/5xx) → on **garde** en file et on s'arrête, comme
      // une panne réseau. (Mélanger les deux serait une perte de score silencieuse, ADR-0037.)
      if (erreur instanceof ErreurApi && !estRefusDefinitif(erreur.statut)) {
        return { traites, refuses, interrompu: true }
      }
      if (erreur instanceof ErreurApi) {
        traites.push(acte)
        refuses.push(acte)
        continue
      }
      // Toute autre erreur = le `fetch` a **rejeté** (panne réseau) : de nouveau hors-ligne, on garde
      // le reste en file et on s'arrête là.
      return { traites, refuses, interrompu: true }
    }
  }
  return { traites, refuses, interrompu: false }
}
