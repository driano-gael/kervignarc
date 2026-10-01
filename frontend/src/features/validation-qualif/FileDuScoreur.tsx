// La file du scoreur (E04US019, planche S07 variante A) : les cibles qui attendent une validation,
// la plus ancienne en tête. L'ordre et l'attente viennent du serveur ; ici on ne fait que les lire.

import { MessageErreur } from '../../shared/ui/MessageErreur'
import { libelleAttente } from './etat'
import { useFileScoreur } from './hooks'

export function FileDuScoreur({
  tournoiId,
  departId,
  onChoisir,
}: {
  tournoiId: number
  departId: number | null
  onChoisir: (archerId: number) => void
}) {
  const file = useFileScoreur(tournoiId, departId)
  const cibles = file.data ?? []

  return (
    <div>
      {/* Le compte n'est dit que s'il est **su** : en chargement ou en erreur, « 0 en attente » se
          lirait « rien à faire » (revue E04US019). */}
      <h4 className="carte__titre">
        File d'attente
        {file.isSuccess && ` — ${cibles.length} cible${cibles.length > 1 ? 's' : ''} en attente`}
      </h4>
      <MessageErreur erreur={file.error} />
      {file.isSuccess && cibles.length === 0 && (
        <p className="carte__etat">Rien à valider : les cibles tirent encore.</p>
      )}
      {cibles.length > 0 && (
        <ul className="validation-liste" aria-label="Cibles en attente de validation">
          {cibles.map((cible) => (
            <li key={cible.cible_index} className="validation-liste__ligne">
              <span className="validation-liste__volee">
                <strong>Cible {cible.cible_index}</strong> — attend depuis{' '}
                {libelleAttente(cible.attente_secondes)}
              </span>
              <span className="validation-liste__actions">
                {cible.archers.map((archer) => (
                  <button
                    key={archer.archer_id}
                    type="button"
                    aria-label={`Valider la feuille de ${archer.nom} ${archer.prenom}, cible ${cible.cible_index}`}
                    onClick={() => onChoisir(archer.archer_id)}
                  >
                    {archer.nom} {archer.prenom}
                  </button>
                ))}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
