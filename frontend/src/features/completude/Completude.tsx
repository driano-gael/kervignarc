// Écran « **Prêt à terminer ?** » — côté sportif. 2ᵉ membre de la famille « prêt à… », rendu par la
// coquille `jalons/PretA` (ADR-0096).
//
// ⚠️ **Le mot « déroulé » est proscrit du libellé** : la sidebar porte déjà « Suivi du déroulé »,
// et ADR-0076 réserve le mot au plan composé une fois. ⚠️ **Cet écran lit `/completude`, pas
// `/jalons/terminer`** : basculer ajouterait un second poll de 5 s par tablette pour une réponse
// identique. ⚠️ Le bouton « Terminer » n'est **jamais bloqué** (`D-15`) et sa confirmation
// **chiffre les impayés** — le seul moment où les deux mondes doivent se croiser (E16US003, A14).

import { BoutonConfirme } from '../../shared/ui/BoutonConfirme'
import { texteErreur } from '../../shared/ui/texteErreur'
// DETTE-083 — ⚠️ l'autre moitié du cycle : `jalons/PretA` réimporte `completude`.
import { PretA } from '../jalons/PretA'
import type { StatutTournoi } from '../competition/api'
import { useCompletude, useTerminerDepuisCompletude } from './hooks'
import { IMPLICATION_TERMINER, messageConfirmationTerminer } from './presentation'

// Deux intros, et non une. ⚠️ **Une intro est lue en premier et toujours** — c'est la doctrine que
// l'US a écrite pour l'écran voisin sans se l'appliquer ici : « Ce qui reste à jouer **avant de
// pouvoir terminer** » s'affichait sur un tournoi **déjà terminé**, trois lignes au-dessus de « le
// sportif **est figé** ». Même contradiction de temps que l'implication en pied, corrigée un commit
// plus tôt, à l'autre bout du même écran (relevé en revue).
const INTRO_EN_COURS = (
  <>
    Ce qui reste à jouer avant de pouvoir terminer ce tournoi. Les inscriptions et les paiements se
    suivent sur l’axe <strong>Gestion</strong> : ils ne bloquent pas la clôture sportive.
  </>
)

const INTRO_HORS_EN_COURS = (
  <>
    Où en est le sportif de ce tournoi. Les inscriptions et les paiements se suivent sur l’axe{' '}
    <strong>Gestion</strong>.
  </>
)

export function Completude({ tournoiId, statut }: { tournoiId: number; statut: StatutTournoi }) {
  const completude = useCompletude(tournoiId)
  const terminer = useTerminerDepuisCompletude(tournoiId)
  // DETTE-084 — ⚠️ **le raccourci est ici.** Ce booléen redéduit côté front la garde de statut de
  // `terminer` (`domain.jalon.evaluer_terminer`), faute pour cet écran de lire `/jalons/terminer` :
  // il pilote le verdict, la raison et le bloc d'actions. Le `statut` vient de `useTournois()`,
  // **pollé à 5 s sous la coquille admin** depuis la 5ᵉ passe (`competition/hooks.ts`) : la
  // péremption est fermée, il reste la **copie** de la garde et de sa phrase. Voir le registre.
  const enCours = statut === 'en_cours'

  // Contrôle en amont (`P-4`) : la confirmation **chiffre** ce qui reste et dit ce que terminer
  // fige, avant de laisser passer. Le « geste délibéré » des actions massives (taper un mot) relève
  // d'E12US007. Depuis le retour maquettes du 04/08/2026 (A15), la question passe par un vrai
  // dialogue et non plus par `window.confirm` — le chiffrage y devient lisible, ce qu'une boîte
  // native ne permettait pas.

  return (
    <PretA
      question="Prêt à terminer ?"
      intro={enCours ? INTRO_EN_COURS : INTRO_HORS_EN_COURS}
      titreSection="Sportif"
      // ⚠️ **La liste reste rendue quel que soit le statut** — c'est le comportement d'avant l'US, et
      // le vider a été une sur-correction : l'organisateur qui ouvre cet écran **pendant la pause
      // déjeuner** veut justement voir où en est la qualification (relevé en revue). Ce
      // qu'il fallait retirer hors « en cours », c'est le **verdict** — il accusait la liste (« ce
      // qui manque ci-dessous ») alors que terminer n'a aucune garde de contenu. C'est
      // `questionPosee` qui le porte, pas `lignes`.
      lignes={completude.data?.sportif ?? null}
      questionPosee={enCours}
      // Sans `enCours &&` : `pret` n'est lu que par le verdict, déjà gardé par `questionPosee`. Le
      // conjoint était **inerte** — exactement ce qui a fait retirer `!enCours` de `bloquant` un
      // commit plus tôt, non rejoué sur la prop voisine du même appel (5ᵉ passe, trois axes).
      pret={completude.data?.sportif_complet ?? false}
      // Le badge « complet / incomplet » de la section, tel qu'il était avant la migration. Il se
      // passe **à part** de `pret` depuis la revue : sur cet écran les deux valent `sportif_complet`
      // et le rendu ne change pas, mais sur *démarrer* ils diffèrent — `pret` peut être faux avec
      // toutes les lignes vertes sauf un avertissement qui ne bloque pas.
      complet={completude.data?.sportif_complet ?? false}
      // Terminer n'a aucune garde **de contenu** (`D-15`), ⚠️ **mais il a une garde de statut**, et
      // cet écran la redéduit — seul endroit du lot. Avec `bloquant={false}` en dur, un tournoi en
      // pause s'entendait dire « l'application ne vous en empêchera pas » juste avant un 409. La
      // déduction est locale parce que cet écran lit `/completude`, qui ne porte pas de statut
      // (ADR-0096). DETTE-084 — seule garde encore redéduite côté front, inscrite au registre.
      // `false` et non `!enCours` : hors « en cours » le verdict n'est pas rendu, donc la valeur ne
      // serait jamais lue — une prop inerte se lit comme une preuve.
      bloquant={false}
      // ⚠️ Pas de `moment` : le domaine n'en produit pas pour ce membre, et « à la clôture » — écrit
      // ici le temps d'une passe — datait un refus pour une action que l'écran ne propose même pas.
      // DETTE-084 : cette phrase est une **copie** de `MESSAGE_TERMINER_HORS_EN_COURS`, que le front
      // ne peut pas importer ; elle vaut tant que cet écran lit `/completude` et non le jalon.
      detail={enCours ? null : 'Seul un tournoi en cours peut être terminé.'}
      chargement={completude.isPending}
      erreur={
        completude.isError && (
          <p className="carte__etat carte__etat--erreur" role="alert">
            Complétude injoignable — {texteErreur(completude.error)}
          </p>
        )
      }
    >
      {/* Ce que « terminer » implique (`D-17`) : source unique `IMPLICATION_TERMINER`, partagée
          avec le message de confirmation — les deux ne peuvent plus diverger. */}
      {enCours && completude.data && (
        <p className="completude__implication">{IMPLICATION_TERMINER}</p>
      )}

      {/* ⚠️ Les actions sont **hors** de la garde `completude.data`. Elles y étaient, et c'était une
          contradiction avec `D-15` relevée en revue : si la lecture de la complétude échouait (LAN
          coupé à l'ouverture de l'écran), le bouton « Terminer » **disparaissait** — l'appli
          empêchait, au lieu d'avertir. On dégrade comme le fait déjà `FriseCycleDeVie` (`P-3`) : on
          dit qu'on n'a pas pu vérifier ce qui reste, et on laisse passer. Le manque d'information
          ne doit jamais verrouiller la seule action irréversible du produit. */}
      {enCours && !completude.isPending && (
        <div className="completude__actions">
          <BoutonConfirme
            libelle="Terminer le tournoi"
            className="bouton--danger"
            disabled={terminer.isPending}
            enCours={terminer.isPending}
            titre="Terminer ce tournoi ?"
            message="Les résultats sportifs sont figés. Les paiements, eux, restent ouverts."
            detail={
              completude.data
                ? messageConfirmationTerminer(completude.data)
                : 'Impossible de vérifier ce qui reste (complétude injoignable).'
            }
            libelleConfirmer="Terminer"
            ton="danger"
            onConfirmer={() => terminer.mutate()}
          />
          {terminer.isError && (
            <span className="carte__etat--erreur" role="alert">
              {texteErreur(terminer.error)}
            </span>
          )}
        </div>
      )}
      {statut === 'termine' && (
        <p className="carte__etat">
          Ce tournoi est <strong>terminé</strong> : le sportif est figé.
        </p>
      )}
    </PretA>
  )
}
