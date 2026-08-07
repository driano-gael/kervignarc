// Écran de complétude du **déroulé** (E12US005, recentré en E16US003) — « qu'est-ce qui manque pour
// que le tournoi soit fini ? », côté sportif.
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
// sportif, les paiements restent modifiables après. Il ne se garde que sur `sportif_complet`. ⚠️ Son
// message de confirmation, lui, **continue de chiffrer les impayés** (`messageConfirmationTerminer`
// lit `hors_sportif`) — ce n'est pas un résidu du mélange : la confirmation est justement le seul
// moment où les deux mondes doivent se croiser, puisqu'elle annonce ce qui se fige et ce qui reste
// ouvert. Ne pas « nettoyer » ce lien (`presentation.test.ts` le garde).

import { BoutonConfirme } from '../../shared/ui/BoutonConfirme'
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
      <h2 className="carte__titre">Complétude du déroulé</h2>
      <p className="completude__intro">
        Ce qui reste à jouer avant de pouvoir terminer ce tournoi. Les inscriptions et les paiements
        se suivent sur l’axe <strong>Gestion</strong> : ils ne bloquent pas la clôture sportive.
      </p>

      {completude.isPending && <p className="carte__etat">Chargement…</p>}
      {completude.isError && (
        <p className="carte__etat carte__etat--erreur" role="alert">
          Complétude injoignable — {completude.error.message}
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
