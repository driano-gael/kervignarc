// Écran de complétude du tournoi (E12US005) — « qu'est-ce qui manque pour qu'il soit fini ? ».
//
// Pas une barre de progression : une **liste d'états**, le sportif et le hors sportif comptés
// séparément (`D-17`, CDC UX §8.3). L'écran dit aussi **ce que « terminer » implique** et pose le
// **contrôle en amont** de cette action (la seule irréversible, E01US002) : au clic, un avertissement
// chiffre ce qui reste avant de laisser confirmer (`P-4`). Live par poll court (cf. `useCompletude`).
// L'état se rend en **couleur + pastille + texte** (jamais la couleur seule) ; l'alerte = **ambre**,
// jamais rouge (charte, `DV-03`).

import type { StatutTournoi } from '../competition/api'
import type { LigneCompletude } from './api'
import { useCompletude, useTerminerDepuisCompletude } from './hooks'
import {
  afficheEtat,
  detailLigne,
  IMPLICATION_TERMINER,
  messageConfirmationTerminer,
} from './presentation'

export function Completude({ tournoiId, statut }: { tournoiId: number; statut: StatutTournoi }) {
  const completude = useCompletude(tournoiId)
  const terminer = useTerminerDepuisCompletude(tournoiId)

  const demanderTerminer = () => {
    // Contrôle en amont (`P-4`) : la confirmation **chiffre** ce qui reste et dit ce que terminer
    // fige, avant de laisser passer. Confirmation simple (comme la révocation en supervision) — le
    // « geste délibéré » des actions massives (taper un mot) relève d'E12US007.
    if (!completude.data) return
    if (window.confirm(messageConfirmationTerminer(completude.data))) terminer.mutate()
  }

  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">Complétude du tournoi</h2>
      <p className="completude__intro">Ce qui reste avant de pouvoir terminer ce tournoi.</p>

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
          <SectionCompletude titre="Hors sportif" lignes={completude.data.hors_sportif} />

          {/* Ce que « terminer » implique (`D-17`) : source unique `IMPLICATION_TERMINER`, partagée
              avec le message de confirmation — les deux ne peuvent plus diverger. */}
          <p className="completude__implication">{IMPLICATION_TERMINER}</p>

          {statut === 'en_cours' && (
            <div className="completude__actions">
              <button
                type="button"
                className="bouton--danger"
                disabled={terminer.isPending}
                onClick={demanderTerminer}
              >
                Terminer le tournoi
              </button>
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

function SectionCompletude({
  titre,
  lignes,
  complet,
}: {
  titre: string
  lignes: LigneCompletude[]
  complet?: boolean
}) {
  return (
    <div className="completude__section">
      <h3 className="completude__titre">
        {titre}
        {complet !== undefined && (
          <span className={complet ? 'completude__resume--ok' : 'completude__resume--alerte'}>
            {complet ? 'complet' : 'incomplet'}
          </span>
        )}
      </h3>
      <ul className="completude__liste">
        {lignes.map((ligne) => (
          <LigneCompletudeVue key={ligne.cle} ligne={ligne} />
        ))}
      </ul>
    </div>
  )
}

function LigneCompletudeVue({ ligne }: { ligne: LigneCompletude }) {
  const { classe, libelle } = afficheEtat(ligne.etat)
  const detail = detailLigne(ligne)
  return (
    <li className="completude__ligne">
      <span className="completude__libelle">{ligne.libelle}</span>
      <span className={`completude__etat completude__etat--${classe}`}>
        <span className="indicateur__pastille" aria-hidden="true" />
        {detail ?? libelle}
        {detail && <span className="completude__mention">{libelle}</span>}
      </span>
    </li>
  )
}
