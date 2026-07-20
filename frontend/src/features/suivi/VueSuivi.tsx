// Vue « suivi » de l'appli publique (E07US006) — « je retrouve mes archers sans chercher ».
//
// Deux gestes : **rechercher** un archer par son nom pour le **suivre**, et voir la **carte** de chaque
// archer suivi — sa cible / position / départ, à jour en direct. Le choix des archers suivis est
// mémorisé localement (`sessionSuivisStore`, `localStorage`) : aux ouvertures suivantes, la vue s'ouvre
// directement sur eux. Aucun compte, aucune authentification — la lecture publique est anonyme.
//
// **Source des données** : la journée d'un archer se reconstruit depuis **la liste des départs**
// (`useDeparts`, numéro/horaire) et **les plans de cibles** (`getPlanDeCibles`/`useQueries`, la place).
// On n'utilise **pas** l'endpoint des inscriptions : son DTO porte `paye`/`montant_du_centimes` — des
// données financières nominatives qui ne doivent pas atteindre le navigateur d'un spectateur anonyme
// (règle 6 ; correctif de revue B/C1). Les départs et les plans, eux, sont des surfaces publiques sans
// donnée personnelle.
//
// Le live est **gratuit** : ces hooks sont de l'état serveur React Query, invalidé globalement par la
// diffusion temps réel post-commit (E04US009) ; un **déplacement de placement** (admin) ou un
// **rattachement** rafraîchit la carte sans action de l'utilisateur.
//
// La carte couvre le « où il tire » (cible/position/départ) **et** le **déroulé du tour en direct**
// (E07US009, ADR-0039) : les volées du jour, chacune avec son statut « en attente de validation » /
// « validé ». L'**à-venir** (prochaine phase/cible) reste E07US008.

import { useState } from 'react'
import { useQueries } from '@tanstack/react-query'
import { useArchers } from '../archers/hooks'
import type { Archer } from '../competition/api'
import type { Depart } from '../departs/api'
import { useDeparts } from '../departs/hooks'
import { getPlanDeCibles, type PlanDeCibles } from '../placement/api'
import { clePlan } from '../placement/hooks'
import { type ArcherSuivi, useSessionSuivisStore } from '../../shared/stores/sessionSuivisStore'
import { useDeroule } from './deroule'
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
        enChargement={archersQuery.isLoading}
        enErreur={archersQuery.isError}
        tournoiId={tournoiId}
        suivis={suivisIci}
      />

      {suivisIci.length > 0 && (
        <ul className="suivis">
          {suivisIci.map((s) => (
            <CarteArcherSuivi
              key={s.archerId}
              tournoiId={tournoiId}
              archerId={s.archerId}
              archer={archersParId.get(s.archerId) ?? null}
              // « a réussi à charger », pas « ne charge plus » : sur erreur, `isLoading` est aussi
              // faux — confondre les deux ferait passer une coupure réseau pour un archer disparu
              // (correctif de revue C1/adversarial).
              archersReussi={archersQuery.isSuccess}
              archersEnErreur={archersQuery.isError}
              departs={departs}
              plansParDepart={plansParDepart}
              chargement={archersQuery.isLoading || chargementPlans}
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
  enChargement,
  enErreur,
  tournoiId,
  suivis,
}: {
  archers: Archer[]
  enChargement: boolean
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
        // On ne présente jamais une erreur ni un chargement comme un « aucun archer » (fait négatif) :
        // erreur d'abord, puis résultats, puis chargement, et seulement en dernier « aucun » (revue C1).
        (enErreur ? (
          <p className="carte__etat carte__etat--erreur">
            Liste momentanément indisponible — connexion perdue.
          </p>
        ) : resultats.length > 0 ? (
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
        ) : enChargement ? (
          <p className="carte__etat">Chargement…</p>
        ) : (
          <p className="carte__etat">Aucun archer à ce nom.</p>
        ))}
    </div>
  )
}

// La carte d'un archer suivi : son nom, le bouton « ne plus suivre », et sa journée (une ligne par
// départ où il est posé). `archer` peut être `null` un court instant (liste pas encore chargée) → repli
// `Archer #id` ; s'il reste `null` alors que la liste a **réussi** à charger, c'est qu'il a été retiré
// du tournoi → on le dit (mais une **erreur** de chargement n'est pas une disparition — revue C1).
function CarteArcherSuivi({
  tournoiId,
  archerId,
  archer,
  archersReussi,
  archersEnErreur,
  departs,
  plansParDepart,
  chargement,
  erreur,
}: {
  tournoiId: number
  archerId: number
  archer: Archer | null
  archersReussi: boolean
  archersEnErreur: boolean
  departs: Depart[]
  plansParDepart: Map<number, PlanDeCibles>
  chargement: boolean
  erreur: boolean
}) {
  const nePlusSuivre = useSessionSuivisStore((s) => s.nePlusSuivre)
  const journee = construireJournee(archerId, departs, plansParDepart)
  const nom = archer ? `${archer.prenom} ${archer.nom}` : `Archer #${archerId}`
  const archerDisparu = archer === null && archersReussi

  // Le déroulé du tour (E07US009) : de l'état serveur, invalidé en live par le temps réel. On ne
  // montre le bloc que s'il y a des volées — sans saisie, l'endpoint rend un déroulé vide (pas une
  // erreur), et la carte reste sur « où il tire » sans afficher de section creuse.
  const deroule = useDeroule(tournoiId, archerId).data
  const volees = deroule?.volees ?? []

  return (
    <li className="carte carte-suivi">
      <div className="carte-suivi__entete">
        <strong className="carte-suivi__nom">{nom}</strong>
        <button type="button" className="lien" onClick={() => nePlusSuivre(archerId)}>
          Ne plus suivre
        </button>
      </div>

      {/* On montre d'abord la journée qu'on CONNAÎT : l'échec d'un seul plan ne doit pas masquer la
          place déjà chargée sur un autre départ (revue C1, F2). L'erreur ne s'affiche que faute de
          mieux. */}
      {journee.length > 0 ? (
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
      ) : archerDisparu ? (
        <p className="carte__etat">Cet archer n’est plus dans le tournoi.</p>
      ) : archersEnErreur || erreur ? (
        <p className="carte__etat">
          Connexion momentanément perdue — mise à jour au retour du réseau.
        </p>
      ) : chargement ? (
        <p className="carte__etat">Chargement…</p>
      ) : (
        <p className="carte__etat">Pas encore placé.</p>
      )}

      {volees.length > 0 && (
        <div className="suivi-deroule">
          <ul className="suivi-deroule__volees">
            {volees.map((v) => (
              <li key={v.numero} className="suivi-volee">
                <span className="suivi-volee__num">V{v.numero}</span>
                <span className="suivi-volee__valeurs">{v.valeurs.join(' ')}</span>
                <span className="suivi-volee__points">{v.points}</span>
                {/* Statut : « en attente » = alerte ambre (état légitime, DV-03), pas une erreur ;
                    les scores non validés sont provisoires (ADR-0039). « validé » est neutre. */}
                <span
                  className={
                    v.statut === 'valide'
                      ? 'suivi-volee__statut suivi-volee__statut--valide'
                      : 'suivi-volee__statut suivi-volee__statut--attente'
                  }
                >
                  {v.statut === 'valide' ? 'validé' : 'en attente'}
                </span>
              </li>
            ))}
          </ul>
          <p className="suivi-deroule__cumul">
            Total validé <strong>{deroule?.cumul ?? 0}</strong>
          </p>
        </div>
      )}
    </li>
  )
}
