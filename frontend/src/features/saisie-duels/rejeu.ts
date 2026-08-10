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
  // Vrai si des actes **restent en file** : panne réseau, ou refus transitoire sur au moins une
  // rencontre. À retenter à la prochaine reconnexion.
  interrompu: boolean
}

/** L'emplacement **de la rencontre**, plus grossier que `cleSlot` (qui distingue chaque acte).
 *
 * C'est la maille à laquelle l'ordre compte : valider suppose les manches de **cette** rencontre
 * déjà rejouées. Deux rencontres différentes, elles, n'ont aucune dépendance entre elles.
 */
function cleRencontre(acte: ActeDuelEnFile): string {
  return `${acte.famille ?? 'tableau'}:${acte.tournoi_id}:${acte.phase_id}:${acte.match_numero}`
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
  // ⚠️ **Un refus transitoire bloque sa rencontre, pas la tablette entière** (correctif de revue
  // E05US023). Le rejeu s'arrêtait au **premier** acte refusé et gardait tout le reste en file. En
  // tableau c'était supportable : un 409 y est réellement passager (`duel_desynchronise` le temps
  // d'un re-seed). En **poules**, il ne l'est pas — le `match_numero` est un compteur qui court sur
  // toute la phase, donc un seul archer ajouté recompose les groupes et désynchronise *toutes* les
  // rencontres déjà tirées, définitivement. Une tablette qui avait saisi pendant une coupure ne
  // drainait alors plus **rien**, y compris les actes des rencontres saines.
  //
  // On garde ce qui compte — l'ordre **par rencontre** — et on abandonne ce qui ne servait à rien :
  // l'ordre entre rencontres distinctes, qu'aucune dépendance ne relie. Les actes bloqués restent
  // en file, `interrompu` reste vrai, donc rien n'est perdu ni marqué traité à tort.
  const bloquees = new Set<string>()
  let interrompu = false
  for (const acte of file) {
    if (!estEncoreEnFile(acte)) continue // superseded entre-temps → ni envoyé, ni « traité »
    if (bloquees.has(cleRencontre(acte))) continue // rencontre en échec : on la laisse en file
    try {
      await envoyer(acte)
      traites.push(acte)
    } catch (erreur) {
      // `ErreurApi` = le serveur a **répondu**. Refus **définitif** (4xx métier) → on retire et on
      // journalise ; **transitoire** (401/409/429/5xx) → on **garde** en file. (Mélanger les deux
      // serait une perte de score silencieuse, ADR-0037.)
      if (erreur instanceof ErreurApi && !estRefusDefinitif(erreur.statut)) {
        bloquees.add(cleRencontre(acte))
        interrompu = true
        continue
      }
      if (erreur instanceof ErreurApi) {
        traites.push(acte)
        refuses.push(acte)
        continue
      }
      // Toute autre erreur = le `fetch` a **rejeté** (panne réseau) : de nouveau hors-ligne, on
      // garde le reste en file et on s'arrête là — cette fois pour de bon, poursuivre ne ferait que
      // collectionner des `fetch` qui pendent.
      return { traites, refuses, interrompu: true }
    }
  }
  return { traites, refuses, interrompu }
}
