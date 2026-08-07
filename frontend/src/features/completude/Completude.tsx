// Écran « **Prêt à terminer ?** » (E12US005, recentré et renommé en E16US003) — « qu'est-ce qui
// manque pour que le tournoi soit fini ? », côté sportif.
//
// **Pourquoi ce nom.** L'écran s'est d'abord appelé « Complétude », puis « Complétude du déroulé » —
// abandonné en revue : la sidebar du pilotage porte déjà « Suivi du déroulé » trois entrées plus
// haut, et ADR-0076 réserve « déroulé » au **plan composé une fois**. Deux libellés voisins pour deux
// choses différentes, c'est le motif exact du refus d'A10 (ADR-0073). Le nom retenu dit la
// **question à laquelle l'écran répond** plutôt que son contenu. Le commanditaire vise à terme une
// famille de « prêt à… » (démarrer / terminer / archiver / exporter) : c'est plus large que cette US
// et c'est écrit dans `stories/E16` — ne pas l'improviser ici.
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
// *terminé* seul ») et le CA d'E12US005 le disent, et `sportif_complet` ne pilote que le **libellé
// de la question** posée à la confirmation (« Terminer quand même ? » vs « Terminer le tournoi ? »,
// cf. `presentation.ts`). Une garde dure ici empêcherait de clore un tournoi pour une cible
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
import type { StatutTournoi } from '../competition/api'
import { useCompletude, useTerminerDepuisCompletude } from './hooks'
import { IMPLICATION_TERMINER, messageConfirmationTerminer } from './presentation'
import { SectionCompletude } from './SectionCompletude'

export function Completude({ tournoiId, statut }: { tournoiId: number; statut: StatutTournoi }) {
  const completude = useCompletude(tournoiId)
  const terminer = useTerminerDepuisCompletude(tournoiId)

  // Contrôle en amont (`P-4`) : la confirmation **chiffre** ce qui reste et dit ce que terminer
  // fige, avant de laisser passer. Le « geste délibéré » des actions massives (taper un mot) relève
  // d'E12US007. Depuis le retour maquettes du 04/08/2026 (A15), la question passe par un vrai
  // dialogue et non plus par `window.confirm` — le chiffrage y devient lisible, ce qu'une boîte
  // native ne permettait pas.

  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">Prêt à terminer ?</h2>
      <p className="completude__intro">
        Ce qui reste à jouer avant de pouvoir terminer ce tournoi. Les inscriptions et les paiements
        se suivent sur l’axe <strong>Gestion</strong> : ils ne bloquent pas la clôture sportive.
      </p>

      {completude.isPending && <p className="carte__etat">Chargement…</p>}
      {completude.isError && (
        <p className="carte__etat carte__etat--erreur" role="alert">
          Complétude injoignable — {texteErreur(completude.error)}
        </p>
      )}

      {completude.data && (
        <>
          <SectionCompletude
            titre="Sportif"
            complet={completude.data.sportif_complet}
            lignes={completude.data.sportif}
          />

          {/* Ce que « terminer » implique (`D-17`) : source unique `IMPLICATION_TERMINER`, partagée
              avec le message de confirmation — les deux ne peuvent plus diverger. */}
          <p className="completude__implication">{IMPLICATION_TERMINER}</p>

          {statut === 'en_cours' && (
            <div className="completude__actions">
              <BoutonConfirme
                libelle="Terminer le tournoi"
                className="bouton--danger"
                disabled={terminer.isPending || !completude.data}
                enCours={terminer.isPending}
                titre="Terminer ce tournoi ?"
                message="Les résultats sportifs sont figés. Les paiements, eux, restent ouverts."
                detail={completude.data ? messageConfirmationTerminer(completude.data) : null}
                libelleConfirmer="Terminer"
                ton="danger"
                onConfirmer={() => terminer.mutate()}
              />
              {terminer.isError && (
                <span className="carte__etat--erreur" role="alert">
                  {terminer.error.message}
                </span>
              )}
            </div>
          )}
          {statut === 'termine' && (
            <p className="carte__etat">
              Ce tournoi est <strong>terminé</strong> : le sportif est figé.
            </p>
          )}
        </>
      )}
    </section>
  )
}
