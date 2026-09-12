// L'accueil parle **par départ** (E16US021, CA A02) — un bloc par créneau, tous côte à côte.
//
// « Une fois un tournoi choisi, on arrive sur la page du déroulé du tournoi avec un accueil qui
// reprend les informations du tournoi par départ dans un grand encart ». L'accueil **lit** : l'état
// de cycle et l'effectif sont dérivés par le serveur (`GET /tournois/{id}/departs`), la pause vient
// de la route que le pilotage polle déjà. Rien n'est recalculé ici.

import { useQueries } from '@tanstack/react-query'

import { phraseDeRelance, resumeDeRelance } from '../../shared/phases/relance'
import { texteErreur } from '../../shared/ui/texteErreur'
import { useMaintenant } from '../../shared/ui/useMaintenant'
import type { Depart } from '../departs/api'
import { libelleEtatDepart } from '../departs/courant'
import { useDeparts } from '../departs/hooks'
import { getArretsEnAttente } from '../suivi-deroule/api'
import { INTERVALLE_POLL_MS, RACINE_ARRETS } from '../suivi-deroule/hooks'

export function BlocsParDepart({ tournoiId }: { tournoiId: number }) {
  const departs = useDeparts(tournoiId)
  const creneaux = departs.data ?? []
  // Battement à la minute — le grain affiché du « depuis x min ». Cf. `useMaintenant` : lire
  // l'horloge pendant le rendu est une impureté, et le compteur resterait figé tant que le serveur
  // renvoie la même réponse.
  const maintenant = useMaintenant(60000)
  // ⚠️ **Une lecture par créneau, et aucune route neuve** : `useQueries` sur la route que le
  // pilotage polle déjà partage son cache. C'est le coût qu'assumait déjà la pastille de relance
  // que ces blocs remplacent — donc pas un aller-retour de plus qu'avant l'US.
  const arretsParCreneau = useQueries({
    queries: creneaux.map((depart) => ({
      queryKey: [...RACINE_ARRETS, depart.id] as const,
      queryFn: () => getArretsEnAttente(depart.id),
      // Même cadence que `useArretsEnAttente`, dont on partage la clé de cache : recopier la valeur
      // à la main les aurait fait diverger au premier ajustement (revue E05US034).
      refetchInterval: INTERVALLE_POLL_MS,
      staleTime: 0,
    })),
  })

  if (departs.isError) {
    return (
      <p className="carte__etat carte__etat--erreur" role="alert">
        Créneaux injoignables — {texteErreur(departs.error)}
      </p>
    )
  }
  // Rien plutôt qu'un cadre vide tant qu'on ne sait pas : un bloc qui apparaît puis se remplit se
  // lit comme un incident sur un écran qui se rafraîchit tout seul.
  if (departs.isLoading) return null
  if (creneaux.length === 0) {
    return <p className="carte__etat">Aucun créneau : ce tournoi n’a pas encore de départ.</p>
  }

  return (
    <ul className="departs-accueil">
      {creneaux.map((depart, rang) => (
        <BlocDepart
          key={depart.id}
          depart={depart}
          // `?? []` et non `.data!` : un créneau dont la lecture d'arrêts a échoué rend son bloc
          // sans la ligne de pause — l'horaire et l'effectif restent lisibles. Ne jamais perdre
          // tout le bloc sur le hoquet de sa donnée la plus accessoire (`P-3`).
          resume={resumeDeRelance(arretsParCreneau[rang]?.data ?? [], maintenant)}
        />
      ))}
    </ul>
  )
}

function BlocDepart({
  depart,
  resume,
}: {
  depart: Depart
  resume: ReturnType<typeof resumeDeRelance>
}) {
  return (
    <li className={`depart-accueil depart-accueil--${depart.etat}`}>
      <p className="depart-accueil__entete">
        <span className="depart-accueil__numero">Départ&nbsp;{depart.numero}</span>
        <span className="depart-accueil__horaire">{depart.horaire}</span>
        {/* `DV-03` — le mot porte le sens, la couleur ne fait que le renforcer. */}
        <span className="depart-accueil__etat">{libelleEtatDepart(depart)}</span>
      </p>
      <p className="depart-accueil__effectif">
        <span className="depart-accueil__chiffre">
          {depart.quota === null ? depart.effectif : `${depart.effectif}/${depart.quota}`}
        </span>{' '}
        inscrit{depart.effectif > 1 ? 's' : ''}
        {depart.quota !== null && ' (quota)'}
      </p>
      {resume !== null && (
        <p className="carte__etat carte__etat--alerte" role="status">
          <strong>{phraseDeRelance(resume)}</strong> Le tir est suspendu&nbsp;: relancez depuis
          «&nbsp;Suivi du déroulé&nbsp;».
        </p>
      )}
    </li>
  )
}
