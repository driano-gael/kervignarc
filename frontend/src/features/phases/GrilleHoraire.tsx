// Le **déroulé horaire** du tournoi (E03US010, CA 6) : une ligne par étape, une colonne par départ.
// Les heures sont calculées par le serveur depuis les durées (ADR-0118) ; cet écran ne fait que lire.

import { LIBELLE_TYPE } from '../../shared/phases/catalogue'
import { decrireDuree, decrireHeure } from '../../shared/phases/horaires'
import { messageDeLecture } from '../../shared/api/etatDeLecture'
import type { EtapeDeroule, HoraireEtape } from './api'
import { useHorairesPrevus } from './hooks'

export function GrilleHoraire({
  tournoiId,
  etapes,
}: {
  tournoiId: number
  etapes: EtapeDeroule[]
}) {
  const horaires = useHorairesPrevus(tournoiId)
  const creneaux = horaires.data

  return (
    <section aria-labelledby="titre-grille-horaire">
      <h4 className="carte__soustitre" id="titre-grille-horaire">
        Déroulé horaire prévu
      </h4>
      <p className="carte__aide">
        Calculé depuis l’heure de chaque départ et la durée prévue de chaque phase : une phase
        commence quand les phases qui l’alimentent sont finies. Réglez les durées dans la fiche de
        chaque phase.
      </p>
      {creneaux === undefined ? (
        <p className="carte__etat">{messageDeLecture(horaires)}</p>
      ) : creneaux.length === 0 ? (
        <p className="carte__etat">Aucun départ n’est défini : aucune heure ne peut se calculer.</p>
      ) : (
        <div className="table-defilement">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Phase</th>
                <th scope="col">Durée</th>
                {creneaux.map((creneau) => (
                  <th scope="col" key={creneau.depart_id}>
                    Départ {creneau.numero} ({creneau.horaire})
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {etapes.map((etape) => (
                <tr key={etape.id}>
                  <th scope="row">
                    {etape.ordre}. {etape.titre ?? LIBELLE_TYPE[etape.type]}
                  </th>
                  <td>{etape.duree_prevue === null ? '—' : decrireDuree(etape.duree_prevue)}</td>
                  {creneaux.map((creneau) => (
                    <td key={creneau.depart_id}>
                      {decrireCase(creneau.etapes.find((h) => h.etape_id === etape.id))}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

// `undefined` : l'étape vient d'être ajoutée et la grille n'est pas encore relue — rien à affirmer.
function decrireCase(horaire: HoraireEtape | undefined): string {
  if (horaire === undefined) return '—'
  return `${decrireHeure(horaire.debut)} → ${decrireHeure(horaire.fin)}`
}
