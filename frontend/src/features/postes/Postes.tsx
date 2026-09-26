// Rubrique admin « Postes de cible » (E04US001) — préparer et afficher les codes de cible.
//
// L'admin prépare, **à l'avance** (D-07), un code par cible du plan de salle ; chaque code sera
// imprimé sous le QR de sa cible (E09US008) et collé dessus. La tablette posée sur la cible s'y
// rattache en scannant le QR, ou en tapant ce code (E04US001, écran de poste). La préparation est
// **idempotente** : la relancer complète les cibles manquantes sans changer les codes déjà émis.

import { MessageErreur } from '../../shared/ui/MessageErreur'
import { QrCible } from './QrCible'
import { usePostes, usePreparerPostes, useTelechargerEtiquettesQr } from './hooks'

export function Postes({ tournoiId }: { tournoiId: number }) {
  const postes = usePostes(tournoiId)
  const preparer = usePreparerPostes(tournoiId)
  const etiquettes = useTelechargerEtiquettesQr(tournoiId)
  const liste = postes.data ?? []
  const erreur = preparer.error ?? postes.error ?? etiquettes.error

  return (
    <section className="carte">
      <h3 className="carte__titre">Postes de cible</h3>
      <p className="carte__etat">
        Chaque cible reçoit un <strong>code</strong> et son <strong>QR</strong> : la tablette posée
        sur la cible s'y rattache en scannant le QR affiché (touchez-le pour l'agrandir), ou en
        tapant ce code.
      </p>
      <div className="formulaire__actions">
        <button type="button" disabled={preparer.isPending} onClick={() => preparer.mutate()}>
          {liste.length === 0 ? 'Préparer les codes de cible' : 'Compléter les codes manquants'}
        </button>
        {/* **Imprimer toutes les étiquettes** (A12 : *« les QR peuvent être imprimés en avance
            et/ou affichés sur l'écran à la demande »*). L'affichage à la demande existait ; le PDF,
            lui, était livré côté serveur depuis E09US008 mais n'était atteignable depuis **aucun
            écran** — une fonctionnalité complète et invisible. */}
        {liste.length > 0 && (
          <button
            type="button"
            className="bouton--discret"
            disabled={etiquettes.isPending}
            onClick={() => etiquettes.mutate()}
          >
            {etiquettes.isPending ? 'Génération…' : 'Imprimer toutes les étiquettes (PDF)'}
          </button>
        )}
      </div>

      <MessageErreur erreur={erreur} />

      {liste.length > 0 ? (
        // Planche A12, variante « liste des postes avec dernier signe de vie » (E17US012) : une
        // ligne par poste de cible, son QR à la ligne. RATTACHEMENT, APPAREIL et SIGNE DE VIE
        // restent à la supervision (A13), TYPE est retiré — cet écran ne liste que des cibles.
        <div className="table-defilement">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Poste</th>
                <th scope="col">Code</th>
                <th scope="col">QR</th>
              </tr>
            </thead>
            <tbody>
              {liste.map((poste) => (
                <tr key={poste.id}>
                  <td>Cible {poste.cible_index}</td>
                  <td>
                    <code>{poste.code}</code>
                  </td>
                  <td>
                    <QrCible tournoiId={tournoiId} cibleIndex={poste.cible_index} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
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
