// Écran « Exports & impressions » de l'appli admin (E09US003, formats E16US007).
//
// ⚠️ **L'écran ne connaît aucun format** : les boutons d'un document sont produits depuis le
// catalogue servi par le serveur (ADR-0101). Il connaît en revanche le **chemin** et les
// **commandes** de chaque document (tri, départ) : c'est de l'IHM, et c'est la contrepartie
// assumée du même ADR — ajouter un format ne touche pas ce fichier, ajouter un document si.

import { type ReactNode, useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useDeparts } from '../departs/hooks'
import {
  cheminClubPaiement,
  cheminFeuilleDeMarque,
  cheminPlacement,
  type EntreeCatalogueExport,
  type TriPlacement,
} from './api'
import { useCatalogueExports, useTelechargerExport } from './hooks'

// Ce que l'écran ajoute à une entrée du catalogue : où demander le document, sous quel nom
// l'enregistrer, et les commandes qui le paramètrent. `chemin: null` = commandes incomplètes.
interface DocumentDeLEcran {
  identifiant: string
  chemin: string | null
  nomSansExtension: string
  commandes?: ReactNode
  indisponible?: string
}

function SectionExport({ entree, doc }: { entree: EntreeCatalogueExport; doc: DocumentDeLEcran }) {
  const telecharger = useTelechargerExport()

  return (
    <section>
      <h4 className="carte__soustitre">{entree.libelle}</h4>
      <p className="carte__etat">{entree.description}</p>
      <div className="formulaire formulaire--colonne">
        {doc.commandes}
        <div className="formulaire__actions">
          {entree.formats.map((format) => (
            <button
              key={format.code}
              type="button"
              disabled={telecharger.isPending || doc.chemin === null}
              onClick={() =>
                doc.chemin !== null &&
                telecharger.mutate({
                  chemin: doc.chemin,
                  nomSansExtension: doc.nomSansExtension,
                  format: format.code,
                })
              }
            >
              {telecharger.isPending ? 'Génération…' : `Télécharger (${format.libelle})`}
            </button>
          ))}
        </div>
        {doc.chemin === null && doc.indisponible !== undefined && (
          <p className="carte__etat">{doc.indisponible}</p>
        )}
        <MessageErreur erreur={telecharger.error} />
      </div>
    </section>
  )
}

export function Exports({ tournoiId }: { tournoiId: number }) {
  const departs = useDeparts(tournoiId)
  const catalogue = useCatalogueExports()
  const [tri, setTri] = useState<TriPlacement>('cible')
  const [departId, setDepartId] = useState<number | null>(null)
  const [departFeuille, setDepartFeuille] = useState<number | null>(null)

  const listeDeparts = departs.data ?? []
  const suffixePlacement = departId !== null ? `-depart-${departId}` : ''

  // DETTE-095 (../../../../docs/dette.md) : une entrée du catalogue dont l'`identifiant` manque
  // à cette table n'est **pas rendue**, en silence — rien ne rapproche les deux listes.
  const documents: DocumentDeLEcran[] = [
    {
      identifiant: 'placement',
      chemin: cheminPlacement(tournoiId, { tri, departId }),
      nomSansExtension: `placement-tournoi-${tournoiId}${suffixePlacement}`,
      commandes: (
        <>
          <label className="formulaire__libelle">
            Trier par
            <select
              className="formulaire__champ"
              value={tri}
              onChange={(e) => setTri(e.target.value as TriPlacement)}
            >
              <option value="cible">Cible (ordre de la salle)</option>
              <option value="nom">Nom de l'archer</option>
            </select>
          </label>
          <label className="formulaire__libelle">
            Départ
            <select
              className="formulaire__champ"
              value={departId ?? ''}
              onChange={(e) => setDepartId(e.target.value === '' ? null : Number(e.target.value))}
            >
              <option value="">Tous les départs</option>
              {listeDeparts.map((depart) => (
                <option key={depart.id} value={depart.id}>
                  Départ {depart.numero}
                </option>
              ))}
            </select>
          </label>
        </>
      ),
    },
    {
      identifiant: 'club-paiement',
      chemin: cheminClubPaiement(tournoiId),
      nomSansExtension: `club-paiement-tournoi-${tournoiId}`,
    },
    {
      identifiant: 'feuille-de-marque',
      // Le départ est **obligatoire** ici (il est dans le chemin), au contraire du placement où il
      // filtre. D'où le bouton inactif tant qu'aucun n'est choisi, plutôt qu'un appel qui partirait
      // en 404.
      chemin: departFeuille === null ? null : cheminFeuilleDeMarque(tournoiId, departFeuille),
      nomSansExtension: `feuille-de-marque-tournoi-${tournoiId}-depart-${departFeuille ?? 0}`,
      indisponible: 'Choisissez le départ dont vous voulez les feuilles.',
      commandes: (
        <label className="formulaire__libelle">
          Départ
          <select
            className="formulaire__champ"
            value={departFeuille ?? ''}
            onChange={(e) =>
              setDepartFeuille(e.target.value === '' ? null : Number(e.target.value))
            }
          >
            <option value="">Choisir un départ…</option>
            {listeDeparts.map((depart) => (
              <option key={depart.id} value={depart.id}>
                Départ {depart.numero}
              </option>
            ))}
          </select>
        </label>
      ),
    },
  ]

  const entrees = new Map((catalogue.data ?? []).map((entree) => [entree.identifiant, entree]))

  return (
    <section>
      <h3 className="carte__soustitre">Exports & impressions</h3>
      <p className="carte__etat">
        Générez les documents utiles le jour J. Chaque document propose les formats que le serveur
        sait en produire.
      </p>
      <MessageErreur erreur={catalogue.error} />

      {/* ⚠️ `doc`, pas `document` : ce dernier est le DOM global de la page. */}
      {documents.map((doc) => {
        const entree = entrees.get(doc.identifiant)
        return entree === undefined ? null : (
          <SectionExport key={doc.identifiant} entree={entree} doc={doc} />
        )
      })}
    </section>
  )
}
