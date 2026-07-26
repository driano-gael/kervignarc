// Écran « Exports » de l'appli admin (E09US003) — destination prévue au CDC UX §7.1, matérialisée
// ici avec ses deux premières listes imprimables :
//  - **liste de placement** (accueil des archers) : triable par cible ou par nom, filtrable sur un
//    départ (utile pour n'imprimer que le créneau du moment) ;
//  - **liste club & paiement** (administratif) : par club, dû/payé et totaux — tout le tournoi.
//
// Un téléchargement est une **action** (`useMutation`, pas de cache) ; le bouton se désactive pendant
// la génération (`isPending`) et toute erreur (403/500…) s'affiche via `MessageErreur`.

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useDeparts } from '../departs/hooks'
import type { TriPlacement } from './api'
import { useTelechargerClubPaiement, useTelechargerPlacement } from './hooks'

export function Exports({ tournoiId }: { tournoiId: number }) {
  const departs = useDeparts(tournoiId)
  const [tri, setTri] = useState<TriPlacement>('cible')
  const [departId, setDepartId] = useState<number | null>(null)

  const telechargerPlacement = useTelechargerPlacement(tournoiId)
  const telechargerClubPaiement = useTelechargerClubPaiement(tournoiId)

  return (
    <section>
      <h3 className="carte__soustitre">Exports & impressions</h3>
      <p className="carte__etat">
        Générez les listes papier utiles le jour J. Les documents sont produits en PDF, prêts à
        imprimer.
      </p>

      <section>
        <h4 className="carte__soustitre">Liste de placement</h4>
        <p className="carte__etat">
          Qui tire sur quelle cible et à quelle position — pour l'accueil des archers.
        </p>
        <div className="formulaire formulaire--colonne">
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
              {(departs.data ?? []).map((depart) => (
                <option key={depart.id} value={depart.id}>
                  Départ {depart.numero}
                </option>
              ))}
            </select>
          </label>
          <div className="formulaire__actions">
            <button
              type="button"
              disabled={telechargerPlacement.isPending}
              onClick={() => telechargerPlacement.mutate({ tri, departId })}
            >
              {telechargerPlacement.isPending
                ? 'Génération…'
                : 'Télécharger la liste de placement (PDF)'}
            </button>
          </div>
          <MessageErreur erreur={telechargerPlacement.error} />
        </div>
      </section>

      <section>
        <h4 className="carte__soustitre">Liste club & paiement</h4>
        <p className="carte__etat">
          Par club : départs, dû, réglé ou non, et totaux — pour le suivi administratif. Couvre tout
          le tournoi.
        </p>
        <div className="formulaire__actions">
          <button
            type="button"
            disabled={telechargerClubPaiement.isPending}
            onClick={() => telechargerClubPaiement.mutate()}
          >
            {telechargerClubPaiement.isPending
              ? 'Génération…'
              : 'Télécharger la liste club & paiement (PDF)'}
          </button>
        </div>
        <MessageErreur erreur={telechargerClubPaiement.error} />
      </section>
    </section>
  )
}
