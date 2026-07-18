// Rubrique admin « Postes de cible » (E04US001) — préparer et afficher les codes de cible.
//
// L'admin prépare, **à l'avance** (D-07), un code par cible du plan de salle ; chaque code sera
// imprimé sous le QR de sa cible (E09US008) et collé dessus. La tablette posée sur la cible s'y
// rattache en scannant le QR, ou en tapant ce code (E04US001, écran de poste). La préparation est
// **idempotente** : la relancer complète les cibles manquantes sans changer les codes déjà émis.
//
// L'affichage d'erreur est **inliné** ici plutôt que via le composant `MessageErreur` dupliqué
// (DETTE-004) : inutile d'en ajouter une occurrence de plus avant sa factorisation (E00US013).

import { ErreurApi } from '../../shared/api/client'
import { usePostes, usePreparerPostes } from './hooks'

export function Postes({ tournoiId }: { tournoiId: number }) {
  const postes = usePostes(tournoiId)
  const preparer = usePreparerPostes(tournoiId)
  const liste = postes.data ?? []
  const erreur = preparer.error ?? postes.error

  return (
    <section className="carte">
      <h3 className="carte__titre">Postes de cible</h3>
      <p className="carte__etat">
        Chaque cible reçoit un <strong>code</strong> à coller dessus (avec son QR, à venir) : la
        tablette posée sur la cible s'y rattache en scannant le QR, ou en tapant ce code.
      </p>
      <button type="button" disabled={preparer.isPending} onClick={() => preparer.mutate()}>
        {liste.length === 0 ? 'Préparer les codes de cible' : 'Compléter les codes manquants'}
      </button>

      {erreur !== null && (
        <p className="carte__etat carte__etat--erreur" role="alert">
          {erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'}
        </p>
      )}

      {liste.length > 0 ? (
        <ul className="liste-postes">
          {liste.map((poste) => (
            <li key={poste.id}>
              Cible {poste.cible_index} — <code>{poste.code}</code>
            </li>
          ))}
        </ul>
      ) : (
        postes.isSuccess && (
          <p className="carte__etat">
            Aucun code pour le moment. Définissez d'abord le plan de salle, puis préparez les codes.
          </p>
        )
      )}
    </section>
  )
}
