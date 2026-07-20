// Vue « suivi » de l'appli publique (E07US006) — « je retrouve mes archers sans chercher ».
//
// Deux gestes : **rechercher** un archer par son nom pour le **suivre**, et voir la **carte** de chaque
// archer suivi — sa cible / position / départ, à jour en direct. Le choix des archers suivis est
// mémorisé localement (`sessionSuivisStore`, `localStorage`) : aux ouvertures suivantes, la vue s'ouvre
// directement sur eux. Aucun compte, aucune authentification — la lecture publique est anonyme.
//
// Le live est **gratuit** : les hooks (`useArchers`, `useInscriptions`, `usePlanDeCibles`) sont de
// l'état serveur React Query, invalidé par la diffusion temps réel post-commit (E04US009) ; une
// validation de score qui déplace un archer rafraîchit la carte sans action de l'utilisateur.
//
// Cette tranche couvre le « où il tire » (cible/position/départ). Le **déroulé du tour en direct**
// (scores, statut attente/validé) est E07US009 (backend + ADR), l'**à-venir** est E07US008.

import { useState } from 'react'
import { useArchers } from '../archers/hooks'
import type { Archer } from '../competition/api'
import { useInscriptions } from '../inscriptions/hooks'
import { usePlanDeCibles } from '../placement/hooks'
import { type ArcherSuivi, useSessionSuivisStore } from '../../shared/stores/sessionSuivisStore'
import { filtrerArchers, placeDansPlan } from './suivi'

export function VueSuivi({ tournoiId }: { tournoiId: number }) {
  // La liste des suivis est globale ; on ne montre ici que ceux du tournoi affiché (on peut suivre des
  // archers de tournois concurrents).
  const suivisIci = useSessionSuivisStore((s) => s.suivis.filter((x) => x.tournoiId === tournoiId))
  const archersQuery = useArchers(tournoiId)
  const archers = archersQuery.data ?? []
  const archersParId = new Map(archers.map((a) => [a.id, a]))

  return (
    <div>
      <p className="carte__etat">
        Cherchez un archer par son nom et suivez-le : sa cible apparaît ci-dessous, à jour en
        direct, à chaque ouverture de l’appli.
      </p>

      <RechercheArcher archers={archers} tournoiId={tournoiId} suivis={suivisIci} />

      {suivisIci.length > 0 && (
        <ul className="suivis">
          {suivisIci.map((s) => (
            <CarteArcherSuivi
              key={s.archerId}
              tournoiId={tournoiId}
              archerId={s.archerId}
              archer={archersParId.get(s.archerId) ?? null}
            />
          ))}
        </ul>
      )}
    </div>
  )
}

// La recherche : un champ, et sous lui la liste des archers dont le nom correspond. Tant que le champ
// est vide, rien ne s'affiche (D-09 : la recherche est l'exception). Un archer déjà suivi est marqué
// comme tel plutôt que proposé une 2ᵉ fois.
function RechercheArcher({
  archers,
  tournoiId,
  suivis,
}: {
  archers: Archer[]
  tournoiId: number
  suivis: ArcherSuivi[]
}) {
  const [requete, setRequete] = useState('')
  const suivre = useSessionSuivisStore((s) => s.suivre)
  const dejaSuivis = new Set(suivis.map((s) => s.archerId))
  // Borne l'affichage : sur un nom partiel, une liste de club entière n'aide personne à choisir.
  const resultats = filtrerArchers(archers, requete).slice(0, 8)
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
        (resultats.length === 0 ? (
          <p className="carte__etat">Aucun archer à ce nom.</p>
        ) : (
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
        ))}
    </div>
  )
}

// La carte d'un archer suivi : son nom, le bouton « ne plus suivre », et une ligne par départ où il
// est inscrit. `archer` peut être `null` un court instant (liste des archers pas encore chargée) — on
// retombe alors sur un libellé de repli plutôt que de masquer la carte.
function CarteArcherSuivi({
  tournoiId,
  archerId,
  archer,
}: {
  tournoiId: number
  archerId: number
  archer: Archer | null
}) {
  const nePlusSuivre = useSessionSuivisStore((s) => s.nePlusSuivre)
  const inscriptionsQuery = useInscriptions(archerId)
  const inscriptions = inscriptionsQuery.data ?? []
  const nom = archer ? `${archer.prenom} ${archer.nom}` : `Archer #${archerId}`

  return (
    <li className="carte carte-suivi">
      <div className="carte-suivi__entete">
        <strong className="carte-suivi__nom">{nom}</strong>
        <button type="button" className="lien" onClick={() => nePlusSuivre(archerId)}>
          Ne plus suivre
        </button>
      </div>

      {inscriptionsQuery.isLoading ? (
        <p className="carte__etat">Chargement…</p>
      ) : inscriptions.length === 0 ? (
        <p className="carte__etat">Pas encore inscrit à un départ.</p>
      ) : (
        <ul className="suivi-departs">
          {inscriptions.map((i) => (
            <LigneDepartSuivi
              key={i.id}
              tournoiId={tournoiId}
              archerId={archerId}
              departId={i.depart_id}
              numeroDepart={i.numero_depart}
              horaire={i.horaire}
            />
          ))}
        </ul>
      )}
    </li>
  )
}

// Une ligne « départ → place » : le créneau (numéro + horaire) et, s'il est déjà posé, sa cible et sa
// position sur ce départ. On lit le plan **du départ** (pas le champ `cible` de l'archer, ambigu s'il
// tire sur plusieurs créneaux). Non posé (réserve, ou plan pas encore généré) → état neutre.
function LigneDepartSuivi({
  tournoiId,
  archerId,
  departId,
  numeroDepart,
  horaire,
}: {
  tournoiId: number
  archerId: number
  departId: number
  numeroDepart: number
  horaire: string | null
}) {
  const planQuery = usePlanDeCibles(tournoiId, departId)
  const place = planQuery.data ? placeDansPlan(planQuery.data, archerId) : null

  return (
    <li className="suivi-depart">
      <span className="suivi-depart__creneau">
        Départ {numeroDepart}
        {horaire ? ` · ${horaire}` : ''}
      </span>
      {place ? (
        <span className="suivi-depart__place">
          Cible {place.cible} · Pos. {place.position}
        </span>
      ) : (
        <span className="suivi-depart__attente">
          {planQuery.isLoading ? 'Chargement…' : 'Pas encore placé'}
        </span>
      )}
    </li>
  )
}
