// Vue **publique en lecture seule** du plan de cibles (E07US001, CA « plans de cibles »). Un
// spectateur ou un archer choisit un **départ** (créneau) et voit, cible par cible, qui tire à quelle
// position. Aucune authentification, aucune interaction : c'est l'écran d'ajustement `Placement.tsx`
// (E03US004) débarrassé du glisser-déposer, des mutations admin et de la réserve.
//
// Le plan et la liste des archers sont de l'état **serveur** (React Query) : la diffusion temps réel
// post-commit (E04US009) invalide le cache → la vue se met à jour **toute seule** après un
// changement de placement (CA « live »), sans action du lecteur.
//
// Les noms sont résolus côté client (jointure `archer_id → nom`) : le DTO du plan n'expose que des
// identifiants (voir `planConsultation.ts`). Même approche que `Placement.tsx`, factorisée dans la
// fonction pure pour rester testable.
//
// Nommé `PlanCiblesPublic` (et non `PlanConsultation`) pour ne pas entrer en collision de casse avec
// la logique pure `planConsultation.ts` sur les systèmes de fichiers insensibles à la casse (Windows).

import { useMemo, useState } from 'react'
import { useArchers } from '../archers/hooks'
import { useDeparts } from '../departs/hooks'
import { usePlanDeCibles } from './hooks'
import { construirePlanConsultation } from './planConsultation'

// Prénom puis nom, comme sur l'écran de placement (E03US004) : c'est la même surface « qui est posé
// où », on garde la même lecture de l'identité.
function nomComplet(archer: { prenom: string; nom: string }): string {
  return `${archer.prenom} ${archer.nom}`.trim()
}

// Libellé d'un départ dans le sélecteur : son horaire s'il est renseigné, sinon son numéro.
function libelleDepart(depart: { numero: number; horaire: string | null }): string {
  return depart.horaire ? `Départ ${depart.numero} — ${depart.horaire}` : `Départ ${depart.numero}`
}

export function PlanCiblesPublic({ tournoiId }: { tournoiId: number }) {
  const departs = useDeparts(tournoiId)
  // Départ affiché. `null` tant qu'on n'a pas choisi ; on retombe sur le **premier** départ dès que
  // la liste est connue (un plan sans départ choisi n'aurait rien à montrer). On revalide le choix
  // contre la liste **courante** : si le départ choisi disparaît (supprimé en direct), on ne reste
  // pas figé sur un id fantôme (`<select>` sans option, plan 404) — on retombe sur le premier.
  const [departChoisi, setDepartChoisi] = useState<number | null>(null)
  const departsData = departs.data
  const departId =
    departsData?.some((d) => d.id === departChoisi) === true
      ? departChoisi
      : (departsData?.[0]?.id ?? null)

  if (departs.isPending) {
    return <p className="carte__etat">Chargement…</p>
  }
  if (departs.isError) {
    return (
      <p className="carte__etat carte__etat--erreur" role="alert">
        Départs injoignables — {departs.error.message}
      </p>
    )
  }
  if (departs.data.length === 0) {
    return <p className="carte__etat">Aucun départ n’est encore défini pour ce tournoi.</p>
  }

  return (
    <>
      <label className="classement-filtre">
        Départ{' '}
        <select value={departId ?? ''} onChange={(e) => setDepartChoisi(Number(e.target.value))}>
          {departs.data.map((depart) => (
            <option key={depart.id} value={depart.id}>
              {libelleDepart(depart)}
            </option>
          ))}
        </select>
      </label>
      {departId !== null && <GrilleCibles tournoiId={tournoiId} departId={departId} />}
    </>
  )
}

// La grille des cibles d'un départ donné. Séparée pour que le changement de départ remonte des hooks
// dont la clé dépend de `departId` (React Query re-souscrit proprement).
function GrilleCibles({ tournoiId, departId }: { tournoiId: number; departId: number }) {
  const plan = usePlanDeCibles(tournoiId, departId)
  const archers = useArchers(tournoiId)

  const nomParArcher = useMemo(() => {
    const map = new Map<number, string>()
    for (const archer of archers.data ?? []) map.set(archer.id, nomComplet(archer))
    return map
  }, [archers.data])

  const cibles = useMemo(
    () => (plan.data ? construirePlanConsultation(plan.data, nomParArcher) : []),
    [plan.data, nomParArcher],
  )

  if (plan.isPending) {
    return <p className="carte__etat">Chargement…</p>
  }
  if (plan.isError) {
    return (
      <p className="carte__etat carte__etat--erreur" role="alert">
        Plan injoignable — {plan.error.message}
      </p>
    )
  }
  if (cibles.length === 0) {
    return <p className="carte__etat">Aucune cible pour ce départ.</p>
  }

  return (
    <ul className="plan-public">
      {cibles.map((cible) => (
        <li key={cible.index} className="plan-public__cible">
          <span className="plan-public__titre">Cible {cible.index}</span>
          {cible.places.length === 0 ? (
            <span className="plan-public__vide">Libre</span>
          ) : (
            <ul className="plan-public__places">
              {cible.places.map((place) => (
                <li key={place.position} className="plan-public__place">
                  <span className="plan-public__position">{place.position}</span>
                  <span className="plan-public__nom">{place.nom}</span>
                </li>
              ))}
            </ul>
          )}
        </li>
      ))}
    </ul>
  )
}
