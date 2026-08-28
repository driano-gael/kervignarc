// Vue **publique en lecture seule** du plan de cibles (E07US001) : l'écran d'ajustement
// `Placement.tsx` débarrassé du glisser-déposer, des mutations admin et de la réserve.
//
// Le plan et la liste des archers sont de l'état **serveur** : la diffusion temps réel post-commit
// invalide le cache, donc la vue se met à jour **toute seule**. Les noms sont résolus côté client —
// le DTO n'expose que des identifiants. ⚠️ Nommé `PlanCiblesPublic` et non `PlanConsultation` pour
// ne pas entrer en collision de casse avec `planConsultation.ts` sur un système de fichiers
// insensible à la casse (Windows).

import { useMemo, useState } from 'react'
import { useArchers } from '../archers/hooks'
import { useDeparts } from '../departs/hooks'
import { centrerCibles, type ModeAffichage } from '../../shared/suivis/focus'
import { departDeSalle } from '../salle/rotation'
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

export function PlanCiblesPublic({
  tournoiId,
  mode = 'tout',
  suivis = [],
}: {
  tournoiId: number
  /** Bascule « mes archers / tout » (E16US004) : ne garde que les **buttes** où tire un archer
   * suivi. On filtre la cible entière, voisins compris — sur un plan, « où tire mon archer » se
   * cherche par la butte, et masquer ses voisins rendrait la carte illisible. */
  mode?: ModeAffichage
  suivis?: number[]
}) {
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
    // DETTE-050 : deux rendus ad hoc dans ce fichier (celui-ci et « Plan injoignable » plus bas)
    // ne sont pas ralliés à `shared/ui/texteErreur` — `error.message` interpolé brut. Écran
    // **public** : le spectateur lirait « TypeError: Failed to fetch » sur coupure LAN.
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
      {departId !== null && (
        <GrilleCibles tournoiId={tournoiId} departId={departId} mode={mode} suivis={suivis} />
      )}
    </>
  )
}

/** Le plan de cibles **sans sélecteur**, pour une surface sans interaction (écran de salle).
 *
 * Deux défauts corrigés en revue, et le second était le vrai : `PlanCiblesPublic` embarque un
 * `<select>` que personne ne peut actionner sur un écran projeté, et surtout il retombe sur le
 * **premier** départ — le plan affiché restait celui du départ 1 toute la journée. On choisit ici
 * le départ **réellement en cours** : le premier `lance`, sinon le premier ouvert, sinon le
 * premier.
 */
export function PlanCiblesDeSalle({ tournoiId }: { tournoiId: number }) {
  const departs = useDeparts(tournoiId)
  const courant = departDeSalle(departs.data ?? [])

  if (departs.isPending) {
    return <p className="carte__etat">Chargement…</p>
  }
  if (courant === undefined) {
    return <p className="carte__etat">Aucun départ n’est encore défini pour ce tournoi.</p>
  }
  return (
    <>
      <h3 className="carte__soustitre">Plan de cibles — {libelleDepart(courant)}</h3>
      <GrilleCibles tournoiId={tournoiId} departId={courant.id} />
    </>
  )
}

// La grille des cibles d'un départ donné. Séparée pour que le changement de départ remonte des hooks
// dont la clé dépend de `departId` (React Query re-souscrit proprement).
function GrilleCibles({
  tournoiId,
  departId,
  mode = 'tout',
  suivis = [],
}: {
  tournoiId: number
  departId: number
  mode?: ModeAffichage
  suivis?: number[]
}) {
  const plan = usePlanDeCibles(tournoiId, departId)
  const archers = useArchers(tournoiId)

  const nomParArcher = useMemo(() => {
    const map = new Map<number, string>()
    for (const archer of archers.data ?? []) map.set(archer.id, nomComplet(archer))
    return map
  }, [archers.data])

  // Le centrage s'applique au **plan brut** : c'est lui qui porte les `archer_id`, la vue de
  // consultation ne garde que des noms (cf. `planConsultation.ts`). Filtrer après aurait obligé à
  // rapatrier les identifiants dans le DTO d'affichage pour rien.
  const cibles = useMemo(() => {
    if (!plan.data) return []
    const retenues = centrerCibles(plan.data.cibles, mode, suivis)
    return construirePlanConsultation({ ...plan.data, cibles: retenues }, nomParArcher)
  }, [plan.data, nomParArcher, mode, suivis])

  if (plan.isPending) {
    return <p className="carte__etat">Chargement…</p>
  }
  if (plan.isError) {
    // DETTE-050
    return (
      <p className="carte__etat carte__etat--erreur" role="alert">
        Plan injoignable — {plan.error.message}
      </p>
    )
  }
  if (cibles.length === 0) {
    // Deux vides très différents : « ce départ n'a pas de plan » et « aucun de vos archers n'y tire
    // encore ». Les confondre ferait chercher une panne là où il n'y a qu'un filtre.
    return mode === 'suivis' ? (
      <p className="carte__etat">
        {/* ⚠️ **Nommer le geste utile en PREMIER** (2ᵉ passe de revue). Cet écran porte son propre
            sélecteur de départ, et il s'ouvre sur le premier créneau ; l'interrupteur étant armé par
            défaut, le cas banal est « je suis un archer de l'après-midi et je regarde le matin ».
            Ne proposer que « Tout le tournoi » menait alors à un cul-de-sac : on obtenait le plan
            complet **du mauvais départ**, toujours sans son archer. */}
        Aucun des archers que vous suivez n’est placé sur ce départ. Choisissez un autre départ, ou
        passez à « Tout le tournoi » pour voir le plan complet.
      </p>
    ) : (
      <p className="carte__etat">Aucune cible pour ce départ.</p>
    )
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
