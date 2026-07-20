// Vue « suivi » de l'appli publique (E07US006) — « je retrouve mes archers sans chercher ».
//
// Deux gestes : **rechercher** un archer par son nom pour le **suivre**, et voir la **carte** de chaque
// archer suivi — sa cible / position / départ, à jour en direct. Le choix des archers suivis est
// mémorisé localement (`sessionSuivisStore`, `localStorage`) : aux ouvertures suivantes, la vue s'ouvre
// directement sur eux. Aucun compte, aucune authentification — la lecture publique est anonyme.
//
// **Source des données** : la journée d'un archer se reconstruit depuis **la liste des départs**
// (`useDeparts`, numéro/horaire) et **les plans de cibles** (`usePlanDeCibles`/`useQueries`, la place).
// On n'utilise **pas** l'endpoint des inscriptions : son DTO porte `paye`/`montant_du_centimes` — des
// données financières nominatives qui ne doivent pas atteindre le navigateur d'un spectateur anonyme
// (règle 6 ; correctif de revue B/C1). Les départs et les plans, eux, sont des surfaces publiques sans
// donnée personnelle.
//
// Le live est **gratuit** : ces hooks sont de l'état serveur React Query, invalidé globalement par la
// diffusion temps réel post-commit (E04US009) ; un **déplacement de placement** (admin) ou un
// **rattachement** rafraîchit la carte sans action de l'utilisateur.
//
// Cette tranche couvre le « où il tire » (cible/position/départ). Le **déroulé du tour en direct**
// (scores, statut attente/validé) est E07US009 (backend + ADR), l'**à-venir** est E07US008.

import { useState } from 'react'
import { useQueries } from '@tanstack/react-query'
import { useArchers } from '../archers/hooks'
import type { Archer } from '../competition/api'
import type { Depart } from '../departs/api'
import { useDeparts } from '../departs/hooks'
import { getPlanDeCibles, type PlanDeCibles } from '../placement/api'
import { clePlan } from '../placement/hooks'
import { type ArcherSuivi, useSessionSuivisStore } from '../../shared/stores/sessionSuivisStore'
import { construireJournee, filtrerArchers } from './suivi'

// Borne l'affichage des résultats de recherche : au-delà, on invite à préciser plutôt que de dérouler
// tout un club (et de risquer de cacher l'archer cherché en silence).
const MAX_RESULTATS = 8

export function VueSuivi({ tournoiId }: { tournoiId: number }) {
  // Sélecteur **stable** : on lit la référence brute `s.suivis` (le store ne la recrée qu'à une vraie
  // mutation), puis on filtre dans le corps. Filtrer DANS le sélecteur renverrait un tableau neuf à
  // chaque rendu → boucle infinie en Zustand v5 / React 19 (correctif de revue A).
  const suivis = useSessionSuivisStore((s) => s.suivis)
  const suivisIci = suivis.filter((x) => x.tournoiId === tournoiId)

  const archersQuery = useArchers(tournoiId)
  const archers = archersQuery.data ?? []
  const archersParId = new Map(archers.map((a) => [a.id, a]))

  // Départs + plans : la source de « où tire l'archer ». Fetchés une seule fois pour toutes les cartes
  // (React Query partage par clé — même clé que le plan public, cf. `clePlan`). On ne charge les plans
  // que s'il y a au moins un suivi à afficher.
  const departsQuery = useDeparts(tournoiId)
  const departs = departsQuery.data ?? []
  const besoinPlans = suivisIci.length > 0
  const plansResults = useQueries({
    queries: besoinPlans
      ? departs.map((d) => ({
          queryKey: clePlan(tournoiId, d.id),
          queryFn: () => getPlanDeCibles(tournoiId, d.id),
        }))
      : [],
  })
  const plansParDepart = new Map<number, PlanDeCibles>()
  departs.forEach((d, i) => {
    const data = plansResults[i]?.data
    if (data) plansParDepart.set(d.id, data)
  })
  const chargementPlans = departsQuery.isLoading || plansResults.some((r) => r.isLoading)
  const erreurPlans = departsQuery.isError || plansResults.some((r) => r.isError)

  return (
    <div>
      <p className="carte__etat">
        Cherchez un archer par son nom et suivez-le : sa cible apparaît ci-dessous, à jour en
        direct, à chaque ouverture de l’appli.
      </p>

      <RechercheArcher
        archers={archers}
        enErreur={archersQuery.isError}
        tournoiId={tournoiId}
        suivis={suivisIci}
      />

      {suivisIci.length > 0 && (
        <ul className="suivis">
          {suivisIci.map((s) => (
            <CarteArcherSuivi
              key={s.archerId}
              archerId={s.archerId}
              archer={archersParId.get(s.archerId) ?? null}
              archersCharges={!archersQuery.isLoading}
              departs={departs}
              plansParDepart={plansParDepart}
              chargement={chargementPlans}
              erreur={erreurPlans}
            />
          ))}
        </ul>
      )}
    </div>
  )
}

// La recherche : un champ, et sous lui la liste des archers dont le nom correspond. Tant que le champ
// est vide, rien ne s'affiche (D-09 : la recherche est l'exception). Un archer déjà suivi est marqué
// comme tel plutôt que proposé une 2ᵉ fois ; au-delà de MAX_RESULTATS, on invite à préciser.
function RechercheArcher({
  archers,
  enErreur,
  tournoiId,
  suivis,
}: {
  archers: Archer[]
  enErreur: boolean
  tournoiId: number
  suivis: ArcherSuivi[]
}) {
  const [requete, setRequete] = useState('')
  const suivre = useSessionSuivisStore((s) => s.suivre)
  const dejaSuivis = new Set(suivis.map((s) => s.archerId))
  const correspondances = filtrerArchers(archers, requete)
  const resultats = correspondances.slice(0, MAX_RESULTATS)
  const tropDeResultats = correspondances.length > resultats.length
  const requeteVide = requete.trim() === ''

  return (
    <div className="recherche-suivi">
      <input
        className="formulaire__champ"
        value={requete}
        onChange={(e) => setRequete(e.target.value)}
        placeholder="Rechercher un archer…"
        aria-label="Rechercher un archer par son nom"
        autoComplete="off"
      />

      {!requeteVide &&
        (enErreur ? (
          // Liste des archers en échec de chargement : on ne prétend pas « aucun archer », on dit la
          // vérité (correctif de revue C1 — ne pas présenter une erreur réseau comme un fait négatif).
          <p className="carte__etat carte__etat--erreur">
            Liste momentanément indisponible — connexion perdue.
          </p>
        ) : resultats.length === 0 ? (
          <p className="carte__etat">Aucun archer à ce nom.</p>
        ) : (
          <>
            <ul className="recherche-resultats">
              {resultats.map((a) => (
                <li key={a.id} className="recherche-resultat">
                  <span className="recherche-resultat__nom">
                    {a.prenom} {a.nom}
                  </span>
                  {dejaSuivis.has(a.id) ? (
                    <span className="recherche-resultat__suivi">Suivi ✓</span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => {
                        suivre({ archerId: a.id, tournoiId })
                        setRequete('')
                      }}
                    >
                      Suivre
                    </button>
                  )}
                </li>
              ))}
            </ul>
            {tropDeResultats && <p className="carte__etat">Trop de résultats — précisez le nom.</p>}
          </>
        ))}
    </div>
  )
}

// La carte d'un archer suivi : son nom, le bouton « ne plus suivre », et sa journée (une ligne par
// départ où il est posé). `archer` peut être `null` un court instant (liste pas encore chargée) → repli
// `Archer #id` ; s'il reste `null` **après** chargement, c'est qu'il a été retiré du tournoi → on le dit.
function CarteArcherSuivi({
  archerId,
  archer,
  archersCharges,
  departs,
  plansParDepart,
  chargement,
  erreur,
}: {
  archerId: number
  archer: Archer | null
  archersCharges: boolean
  departs: Depart[]
  plansParDepart: Map<number, PlanDeCibles>
  chargement: boolean
  erreur: boolean
}) {
  const nePlusSuivre = useSessionSuivisStore((s) => s.nePlusSuivre)
  const journee = construireJournee(archerId, departs, plansParDepart)
  const nom = archer ? `${archer.prenom} ${archer.nom}` : `Archer #${archerId}`
  const archerDisparu = archer === null && archersCharges

  return (
    <li className="carte carte-suivi">
      <div className="carte-suivi__entete">
        <strong className="carte-suivi__nom">{nom}</strong>
        <button type="button" className="lien" onClick={() => nePlusSuivre(archerId)}>
          Ne plus suivre
        </button>
      </div>

      {archerDisparu ? (
        <p className="carte__etat">Cet archer n’est plus dans le tournoi.</p>
      ) : erreur ? (
        <p className="carte__etat">
          Connexion momentanément perdue — mise à jour au retour du réseau.
        </p>
      ) : journee.length > 0 ? (
        <ul className="suivi-departs">
          {journee.map((l) => (
            <li key={l.departId} className="suivi-depart">
              <span className="suivi-depart__creneau">
                Départ {l.numeroDepart}
                {l.horaire ? ` · ${l.horaire}` : ''}
              </span>
              <span className="suivi-depart__place">
                Cible {l.cible} · Pos. {l.position}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="carte__etat">{chargement ? 'Chargement…' : 'Pas encore placé.'}</p>
      )}
    </li>
  )
}
