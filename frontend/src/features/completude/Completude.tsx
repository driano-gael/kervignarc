// Écran « **Prêt à terminer ?** » (E12US005, recentré et renommé en E16US003) — « qu'est-ce qui
// manque pour que le tournoi soit fini ? », côté sportif.
//
// **Pourquoi ce nom.** L'écran s'est d'abord appelé « Complétude », puis « Complétude du déroulé » —
// abandonné en revue : la sidebar du pilotage porte déjà « Suivi du déroulé » trois entrées plus
// haut, et ADR-0076 réserve « déroulé » au **plan composé une fois**. Deux libellés voisins pour deux
// choses différentes, c'est le motif exact du refus d'A10 (ADR-0073). Le nom retenu dit la
// **question à laquelle l'écran répond** plutôt que son contenu.
//
// **E16US012 — cet écran est devenu le 2ᵉ membre d'une famille.** Ce que la version précédente
// annonçait sans le faire (« le commanditaire vise à terme une famille de prêt à… — ne pas
// l'improviser ici ») est arrivé : quatre écrans « prêt à… » (démarrer / terminer / archiver /
// exporter) partagent désormais une **coquille unique**, `jalons/PretA` (ADR-0096). Le rendu ne
// change pas — même titre, même intro, même liste, même bouton — mais il passe par la coquille, et
// l'écran gagne au passage le **verdict** en tête (« Il reste des choses à faire — l'application ne
// vous en empêchera pas »).
//
// ⚠️ **Cet écran continue de lire `/completude`, pas `/jalons/terminer`.** Les deux rendent la même
// chose, et `test_jalons_api.py` l'épingle plutôt que de le laisser à la vigilance ; mais la
// **confirmation** a besoin en plus du volet administratif pour chiffrer les impayés (cf. plus
// bas). Basculer la liste sur le jalon aurait ajouté un second poll de 5 s par tablette pour une
// réponse identique.
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

const INTRO = (
  <>
    Ce qui reste à jouer avant de pouvoir terminer ce tournoi. Les inscriptions et les paiements se
    suivent sur l’axe <strong>Gestion</strong> : ils ne bloquent pas la clôture sportive.
  </>
)

export function Completude({ tournoiId, statut }: { tournoiId: number; statut: StatutTournoi }) {
  const completude = useCompletude(tournoiId)
  const terminer = useTerminerDepuisCompletude(tournoiId)
  const enCours = statut === 'en_cours'

  // Contrôle en amont (`P-4`) : la confirmation **chiffre** ce qui reste et dit ce que terminer
  // fige, avant de laisser passer. Le « geste délibéré » des actions massives (taper un mot) relève
  // d'E12US007. Depuis le retour maquettes du 04/08/2026 (A15), la question passe par un vrai
  // dialogue et non plus par `window.confirm` — le chiffrage y devient lisible, ce qu'une boîte
  // native ne permettait pas.

  return (
    <PretA
      question="Prêt à terminer ?"
      intro={INTRO}
      titreSection="Sportif"
      // Vides hors « en cours », comme le rend `evaluer_terminer` : la question ne se pose plus,
      // donc la coquille ne rend ni verdict ni section — seulement la raison. Les garder affichait
      // « Pas encore — ce qui manque ci-dessous sera refusé » au-dessus de trois lignes vertes, sur
      // un tournoi terminé (3ᵉ passe de revue, axes C1 et D).
      lignes={enCours ? (completude.data?.sportif ?? null) : []}
      pret={enCours && (completude.data?.sportif_complet ?? false)}
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
      // bloquant de la 2ᵉ passe de revue.
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
      bloquant={!enCours}
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
      {completude.data && <p className="completude__implication">{IMPLICATION_TERMINER}</p>}

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
