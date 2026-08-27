// Écran « **Prêt à terminer ?** » — « qu'est-ce qui manque pour que le tournoi soit fini ? », côté
// sportif. 2ᵉ membre de la famille « prêt à… », rendu par la coquille `jalons/PretA` (ADR-0096).
//
// ⚠️ **Le mot « déroulé » est proscrit du libellé de cet écran** : la sidebar du pilotage porte
// déjà « Suivi du déroulé », et ADR-0076 réserve le mot au **plan composé une fois**.
//
// ⚠️ **Cet écran lit `/completude`, pas `/jalons/terminer`.** Les deux rendent la même chose
// (`test_jalons_api.py` l'épingle), mais basculer sur le jalon ajouterait un second poll de 5 s par
// tablette pour une réponse identique. La **confirmation**, elle, a besoin en plus du volet
// administratif pour chiffrer les impayés (cf. plus bas).
//
// Pas une barre de progression : une **liste d'états** (`D-17`, CDC UX §8.3). L'écran dit aussi **ce
// que « terminer » implique** et pose le **contrôle en amont** de cette action (la seule
// irréversible, E01US002) : au clic, un avertissement chiffre ce qui reste avant de laisser
// confirmer (`P-4`). Live par poll court (cf. `useCompletude`). L'état se rend en **couleur +
// pastille + texte** (jamais la couleur seule) ; l'alerte = **ambre**, jamais rouge (charte,
// `DV-03`).
//
// **E16US003 — la section « Hors sportif » n'est plus ici.** Le questionnaire A14 a refusé l'écran
// sur ce point précis : *« complétude en déroulé n'est pas complétude administrative ; en déroulé on
// est centré sur l'événement »*. Elle se rend désormais sur l'axe **gestion**, en tête de l'écran
// Paiements (`CompletudeAdministrative`), depuis la **même** réponse serveur — le calcul n'est pas
// dupliqué, c'est la destination qui change.
//
// Le bouton « Terminer » **reste ici** (arbitrage confirmé le 07/08/2026) : ce qu'il fige est le
// sportif, les paiements restent modifiables après. ⚠️ Il n'est **jamais bloqué** — ni par le
// sportif, ni par l'administratif : `D-15` (« l'appli n'empêche pas, elle avertit ; blocage =
// *terminé* seul ») et le CA d'E12US005 le disent. `sportif_complet` ne **garde** rien : il choisit
// le **libellé de la question** posée à la confirmation (« Terminer quand même ? » vs « Terminer le
// tournoi ? », cf. `presentation.ts`) et la mention « complet »/« incomplet » de la section. Une garde dure ici empêcherait de clore un tournoi pour une cible
// abandonnée — le contraire de `D-15`.
//
// ⚠️ Son message de confirmation **continue de chiffrer les impayés** (`messageConfirmationTerminer`
// lit `hors_sportif`) — ce n'est pas un résidu du mélange : la confirmation est justement le seul
// moment où les deux mondes doivent se croiser, puisqu'elle annonce ce qui se fige et ce qui reste
// ouvert. C'est aussi le **contrôle compensatoire** de tout ce recentrage : c'est lui qui fait que
// retirer l'administratif de cet écran ne perd rien. Ne pas « nettoyer » ce lien — `Completude.test.tsx`
// garde le **site d'appel** (il ouvre le dialogue et lit les impayés dedans) et `presentation.test.ts`
// la fonction ; il fallait les deux, la fonction seule laissait le câblage libre de disparaître.

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
      // Terminer n'a aucune garde **de contenu** : l'incomplétude change le libellé de la
      // confirmation, jamais le droit de terminer (`D-15`). C'est l'asymétrie que `bloquant` porte.
      //
      // ⚠️ **Mais il a une garde de statut**, et cet écran la redéduit — seul endroit du lot où
      // c'est encore le cas. `ServiceTournois.terminer` n'accepte que `en_cours` ; avec
      // `bloquant={false}` en dur, un tournoi **en pause** (la pause déjeuner du jour J) s'entendait
      // dire « l'application ne vous en empêchera pas » juste avant un 409, et un tournoi terminé
      // lisait « Oui — rien ne s'y oppose » au-dessus de « ce tournoi est terminé ». C'était le
      // bloquant relevé en revue.
      //
      // Pourquoi une déduction locale ici, alors que `PretADemarrer` n'en fait aucune : cet écran
      // lit `/completude`, qui ne porte pas de statut, et le brancher sur `/jalons/terminer`
      // ajouterait un **second poll de 5 s par tablette** pour la même liste — ce qu'ADR-0096 a
      // explicitement écarté. La contrepartie de cet arbitrage, c'est ce miroir d'
      // `domain.jalon.evaluer_terminer`, et les tests qui l'épinglent hors `en_cours`.
      //
      // DETTE-084 — c'est la **seule** garde encore redéduite côté front du lot, et elle est
      // inscrite au registre plutôt que laissée en commentaire : un angle mort qui ne vit qu'en
      // section « Conséquences » d'un ADR n'apparaît à aucun tri de dette. C'est le motif même de
      // DETTE-082, que cette US venait d'écrire sans se l'appliquer (3ᵉ passe, axes A, C2 et D).
      // `false`, et non `!enCours` : hors « en cours » le verdict n'est pas rendu du tout, donc la
      // valeur ne serait **jamais lue** — une prop inerte se lit comme une preuve et n'en est pas
      // une (relevé en revue). Ce que ce drapeau dit, c'est : *quand la question se pose*, terminer
      // passe malgré les manques. La garde de statut, elle, est portée par `questionPosee`.
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
