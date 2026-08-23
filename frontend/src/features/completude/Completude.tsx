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
// ⚠️ `DETTE-083` — l'autre moitié du cycle : `jalons/PretA` réimporte `completude`.
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
      lignes={completude.data?.sportif ?? null}
      pret={completude.data?.sportif_complet ?? false}
      // Le badge « complet / incomplet » de la section, tel qu'il était avant la migration. Il se
      // passe **à part** de `pret` depuis la revue : sur cet écran les deux valent `sportif_complet`
      // et le rendu ne change pas, mais sur *démarrer* ils diffèrent — `pret` peut être faux avec
      // toutes les lignes vertes sauf un avertissement qui ne bloque pas.
      complet={completude.data?.sportif_complet ?? false}
      // Terminer n'a **aucune garde dure** : l'incomplétude change le libellé de la confirmation,
      // jamais le droit de terminer (`D-15`). C'est l'asymétrie que `bloquant` porte, cf. ADR-0096.
      bloquant={false}
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
      {statut === 'en_cours' && !completude.isPending && (
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
