// Console de supervision des postes (E12US001, ADR-0038) — l'écran du jour J.
//
// « Ce n'est pas un graphique de progression : c'est une console de supervision. » Elle distingue
// *ils tirent lentement* (en ligne, mais dernière activité ancienne) de *leur tablette est morte*
// (hors ligne). Live par poll court (cf. `useSupervision`). L'état se rend en **couleur + pastille +
// texte** (jamais la couleur seule) ; hors ligne = **ambre**, pas rouge (arbitrage ADR-0038 / DV-03).

import { ErreurApi } from '../../shared/api/client'
import type { PosteSupervision } from './api'
import { afficheEtat, avancementLibelle } from './etat'
import { useRevoquerPoste, useSupervision } from './hooks'
import { tempsRelatif } from './tempsRelatif'

export function Supervision({ tournoiId }: { tournoiId: number }) {
  const supervision = useSupervision(tournoiId)

  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">Supervision des postes</h2>

      {supervision.isPending && <p className="carte__etat">Chargement…</p>}
      {supervision.isError && (
        <p className="carte__etat carte__etat--erreur" role="alert">
          Supervision injoignable — {supervision.error.message}
        </p>
      )}

      {supervision.data && (
        <>
          <p className="supervision__compteur" role="status">
            <strong>
              {supervision.data.nb_en_ligne}/{supervision.data.nb_total}
            </strong>{' '}
            en ligne
          </p>

          {supervision.data.nb_total === 0 ? (
            <p className="carte__etat">
              Aucun poste préparé pour ce tournoi (préparez les codes de cible dans «&nbsp;Postes de
              cible&nbsp;»).
            </p>
          ) : (
            <table className="table supervision__table">
              <thead>
                <tr>
                  <th scope="col">Cible</th>
                  <th scope="col">État</th>
                  <th scope="col">Dernière activité</th>
                  <th scope="col">Avancement</th>
                  <th scope="col">IP</th>
                  <th scope="col">
                    <span className="sr-only">Action</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {supervision.data.postes.map((poste) => (
                  <LignePoste key={poste.poste_id} poste={poste} tournoiId={tournoiId} />
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </section>
  )
}

function LignePoste({ poste, tournoiId }: { poste: PosteSupervision; tournoiId: number }) {
  const revoquer = useRevoquerPoste(tournoiId)
  const { classe, libelle } = afficheEtat(poste.etat)
  const rattache = poste.etat !== 'non_rattache'

  const demanderRevocation = () => {
    // Garde-fou tactile : révoquer un poste en cours de tir le coupe. Confirmation simple en
    // attendant E12US007 (« alerter par calcul d'impact »), qui généralisera les alertes chiffrées.
    const ok = window.confirm(
      `Révoquer la cible ${poste.cible_index} ? La tablette repassera à l'écran de rattachement.`,
    )
    if (ok) revoquer.mutate(poste.poste_id)
  }

  return (
    <tr>
      <td>Cible {poste.cible_index}</td>
      <td>
        <span className={`supervision__etat supervision__etat--${classe}`}>
          <span className="indicateur__pastille" aria-hidden="true" />
          {libelle}
        </span>
      </td>
      <td>
        {poste.derniere_saisie === null ? '—' : tempsRelatif(poste.derniere_saisie, new Date())}
      </td>
      <td>{avancementLibelle(poste.avancement)}</td>
      {/* IP en diagnostic (D-06), jamais une identité : sert à retrouver physiquement la tablette. */}
      <td className="supervision__ip">{poste.ip ?? '—'}</td>
      <td>
        {rattache && (
          <button
            type="button"
            className="lien"
            disabled={revoquer.isPending}
            onClick={demanderRevocation}
          >
            Révoquer
          </button>
        )}
        {revoquer.isError && (
          <span className="carte__etat--erreur" role="alert">
            {revoquer.error instanceof ErreurApi
              ? revoquer.error.message
              : 'Échec de la révocation.'}
          </span>
        )}
      </td>
    </tr>
  )
}
