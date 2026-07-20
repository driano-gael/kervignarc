// Classement de qualification en direct (E06US001) — surface de **lecture** partagée par la coquille
// admin (destination « Classement en direct ») et la **consultation publique** (E07US001). La prop
// `admin` n'ajoute que la colonne « Placer » (déléguée à `TableClassement`) ; le reste est identique,
// public ou non.
//
// Un filtre par catégorie restreint l'affichage à une catégorie **sans changer les rangs** : le rang
// scratch (global) reste celui du classement complet — on **voit** une catégorie sans perdre la
// position d'ensemble. Le classement se rafraîchit tout seul via l'invalidation temps réel (E04US009).
//
// Extrait de `admin/CoquilleAdmin.tsx` en E07US001 pour être réutilisable hors de la coquille admin :
// une vue de lecture n'a pas à vivre dans le module d'administration.

import { useState } from 'react'
import { useCategories } from '../categories/hooks'
import { useClassement } from './hooks'
import { TableClassement } from './TableClassement'

export function VueClassement({ tournoiId, admin }: { tournoiId: number; admin: boolean }) {
  const [categorieId, setCategorieId] = useState<number | undefined>(undefined)
  const categories = useCategories(tournoiId)
  const classement = useClassement(tournoiId, categorieId)

  return (
    <>
      <h3 className="carte__soustitre">Classement en direct</h3>
      <label className="classement-filtre">
        Catégorie{' '}
        <select
          value={categorieId ?? ''}
          onChange={(e) =>
            setCategorieId(e.target.value === '' ? undefined : Number(e.target.value))
          }
        >
          <option value="">Toutes catégories</option>
          {(categories.data ?? []).map((categorie) => (
            <option key={categorie.id} value={categorie.id}>
              {categorie.libelle}
            </option>
          ))}
        </select>
      </label>
      {classement.isPending && <p className="carte__etat">Chargement…</p>}
      {classement.isError && (
        <p className="carte__etat carte__etat--erreur" role="alert">
          Classement injoignable — {classement.error.message}
        </p>
      )}
      {classement.data && (
        // Conteneur défilant : à 8 colonnes, la table déborde sur mobile (CA « responsive ») — on la
        // laisse défiler horizontalement plutôt que d'écraser les colonnes.
        <div className="table-defilement">
          <TableClassement tournoiId={tournoiId} lignes={classement.data.lignes} admin={admin} />
        </div>
      )}
    </>
  )
}
