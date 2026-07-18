// Écran d'ajustement du placement (E03US004, ADR-0024) — réservé à l'admin (monté sous `estAdmin`).
//
// On choisit un départ (créneau), puis on ajuste son plan de cibles au **glisser-déposer** : on
// glisse un jeton d'archer d'une cible à l'autre, vers une case libre (déplacement) ou occupée
// (échange), ou vers la **réserve** (mise à l'écart). Le serveur reste l'autorité : chaque geste est
// un PUT, et un refus (`409 deplacement_invalide`) laisse le plan inchangé — on affiche l'alerte et
// on refetch. Drag & drop **HTML5 natif** (à la souris, écran admin sur PC) : aucune dépendance.

import { useMemo, useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import { useArchers } from '../archers/hooks'
import type { Archer } from '../competition/api'
import { useDeparts } from '../departs/hooks'
import type { CiblePlacee, Conflit, Destination, PlanDeCibles, RaisonConflit } from './api'
import {
  useDeplacer,
  useInscriptionParArcher,
  usePlacerRestants,
  usePlanDeCibles,
  useRegenerer,
} from './hooks'

// Les positions d'une cible sont des lettres ; une cible de capacité N expose les N premières.
const POSITIONS = ['A', 'B', 'C', 'D']

// Libellé lisible de la raison d'une mise en réserve. `en_reserve` est neutre (en attente) ;
// `sans_blason` et `non_place` sont des **anomalies** à traiter (style ambre — DV-03, `--warn`).
const LIBELLE_RAISON: Record<RaisonConflit, string> = {
  sans_blason: 'sans blason',
  non_place: 'aucune cible possible',
  en_reserve: 'en attente',
}

const RAISON_ANOMALIE: Record<RaisonConflit, boolean> = {
  sans_blason: true,
  non_place: true,
  en_reserve: false,
}

export function Placement({ tournoiId }: { tournoiId: number }) {
  const departs = useDeparts(tournoiId)
  const [departId, setDepartId] = useState<number | null>(null)

  const liste = departs.data ?? []

  return (
    <section>
      <h3 className="carte__soustitre">Placement sur les cibles</h3>
      {departs.isSuccess && liste.length === 0 && (
        <p className="carte__etat">
          Aucun départ dans ce tournoi : créez un créneau ci-dessus avant de placer les archers.
        </p>
      )}
      {liste.length > 0 && (
        <select
          className="formulaire__champ"
          value={departId ?? ''}
          onChange={(e) => setDepartId(e.target.value === '' ? null : Number(e.target.value))}
          aria-label="Départ à placer"
        >
          <option value="">Choisir un départ…</option>
          {liste.map((depart) => (
            <option key={depart.id} value={depart.id}>
              Départ {depart.numero}
              {depart.horaire ? ` — ${depart.horaire}` : ''}
            </option>
          ))}
        </select>
      )}
      {/* `key` sur le départ : changer de créneau **remonte** le sous-arbre, ce qui réinitialise
          l'état de drag et les confirmations sans les synchroniser à la main. */}
      {departId !== null && <PlanDepart key={departId} tournoiId={tournoiId} departId={departId} />}
    </section>
  )
}

function PlanDepart({ tournoiId, departId }: { tournoiId: number; departId: number }) {
  const plan = usePlanDeCibles(tournoiId, departId)

  if (plan.isPending) return <p className="carte__etat">Chargement du plan…</p>
  if (plan.isError) {
    return (
      <div>
        <MessageErreur erreur={plan.error} />
        <p className="carte__etat">
          Un plan de cibles suppose qu'un gabarit de salle est appliqué au tournoi (section « Plan
          de salle de ce tournoi »).
        </p>
      </div>
    )
  }
  return <PlanCharge tournoiId={tournoiId} departId={departId} plan={plan.data} />
}

function PlanCharge({
  tournoiId,
  departId,
  plan,
}: {
  tournoiId: number
  departId: number
  plan: PlanDeCibles
}) {
  // Noms des archers (une requête, partagée) ; la correspondance archer → inscription se
  // reconstitue par archer présent dans le plan (faute d'endpoint par départ — cf. rapport d'US).
  const archers = useArchers(tournoiId)
  const archerIds = useMemo(() => {
    const ids = new Set<number>()
    for (const cible of plan.cibles) for (const p of cible.placements) ids.add(p.archer_id)
    for (const conflit of plan.conflits) ids.add(conflit.archer_id)
    return [...ids]
  }, [plan])
  const inscriptionParArcher = useInscriptionParArcher(departId, archerIds)

  const nomParArcher = useMemo(() => {
    const map = new Map<number, string>()
    for (const archer of archers.data ?? []) map.set(archer.id, nomComplet(archer))
    return map
  }, [archers.data])

  const regenerer = useRegenerer(tournoiId, departId)
  const deplacer = useDeplacer(tournoiId, departId)
  const placerRestants = usePlacerRestants(tournoiId, departId)

  // Inscription en cours de glissement + case survolée (surbrillance). L'état vit ici : les cases et
  // la réserve sont des cibles de dépôt qui déclenchent le PUT via `deposer`.
  const [inscriptionGlissee, setInscriptionGlissee] = useState<number | null>(null)
  const [survol, setSurvol] = useState<string | null>(null)
  const [confirmationAnnulation, setConfirmationAnnulation] = useState(false)

  const deposer = (destination: Destination) => {
    setSurvol(null)
    if (inscriptionGlissee === null) return
    deplacer.mutate({ inscriptionId: inscriptionGlissee, destination })
    setInscriptionGlissee(null)
  }

  // « Vide » = aucune cible remplie : le plan n'a jamais été généré (E03US004 : la lecture ne
  // génère pas). On propose alors « Générer », sinon « Annuler les modifications » (même endpoint,
  // mais l'annulation **écrase** les ajustements → confirmation).
  const planVide = plan.cibles.every((cible) => cible.placements.length === 0)
  const planPret = plan.conflits.length === 0 && !planVide

  const jeton = (archerId: number) => ({
    nom: nomParArcher.get(archerId) ?? `Archer #${archerId}`,
    inscriptionId: inscriptionParArcher.get(archerId),
  })

  return (
    <div className="placement">
      <div className="placement__barre">
        {planVide ? (
          <button type="button" disabled={regenerer.isPending} onClick={() => regenerer.mutate()}>
            Générer le plan
          </button>
        ) : confirmationAnnulation ? (
          <>
            <button
              type="button"
              className="bouton--danger"
              disabled={regenerer.isPending}
              onClick={() =>
                regenerer.mutate(undefined, { onSuccess: () => setConfirmationAnnulation(false) })
              }
            >
              Confirmer — écraser les ajustements
            </button>
            <button
              type="button"
              className="bouton--discret"
              onClick={() => setConfirmationAnnulation(false)}
            >
              Annuler
            </button>
          </>
        ) : (
          <button
            type="button"
            className="bouton--discret"
            onClick={() => setConfirmationAnnulation(true)}
          >
            Annuler les modifications
          </button>
        )}
        <button
          type="button"
          className="bouton--discret"
          disabled={placerRestants.isPending || plan.conflits.length === 0}
          onClick={() => placerRestants.mutate()}
        >
          Placer les restants
        </button>
      </div>

      {/* Un refus de déplacement (`409`) est non bloquant : ton **ambre**, pas rouge — le geste
          était légitime, il n'était juste pas applicable ici. Le plan reste la vérité serveur. */}
      {deplacer.error && (
        <p className="placement__alerte" role="alert">
          {messageErreur(deplacer.error)}
        </p>
      )}
      <MessageErreur erreur={regenerer.error} />
      <MessageErreur erreur={placerRestants.error} />

      {planPret && (
        <p className="placement__pret" role="status">
          Plan prêt : tous les archers sont placés.
        </p>
      )}

      <div className="placement__cibles">
        {plan.cibles.map((cible) => (
          <Cible
            key={cible.index}
            cible={cible}
            jeton={jeton}
            survol={survol}
            setSurvol={setSurvol}
            onGlisser={setInscriptionGlissee}
            onDeposer={deposer}
          />
        ))}
      </div>

      <Reserve
        conflits={plan.conflits}
        jeton={jeton}
        survole={survol === 'reserve'}
        setSurvol={setSurvol}
        onGlisser={setInscriptionGlissee}
        onDeposer={() => deposer({ cible_index: null, position: null })}
      />
    </div>
  )
}

type Jeton = { nom: string; inscriptionId: number | undefined }

function Cible({
  cible,
  jeton,
  survol,
  setSurvol,
  onGlisser,
  onDeposer,
}: {
  cible: CiblePlacee
  jeton: (archerId: number) => Jeton
  survol: string | null
  setSurvol: (cle: string | null) => void
  onGlisser: (inscriptionId: number) => void
  onDeposer: (destination: Destination) => void
}) {
  const positions = POSITIONS.slice(0, cible.capacite)

  return (
    <div className="cible">
      <span className="cible__titre">Cible {cible.index}</span>
      <div className="cible__cases">
        {positions.map((position) => {
          const place = cible.placements.find((p) => p.position === position)
          const cle = `${cible.index}:${position}`
          return (
            <Case
              key={position}
              position={position}
              survole={survol === cle}
              onSurvol={(actif) => setSurvol(actif ? cle : null)}
              onDeposer={() => onDeposer({ cible_index: cible.index, position })}
            >
              {place ? (
                <JetonArcher jeton={jeton(place.archer_id)} onGlisser={onGlisser} />
              ) : (
                <span className="case__libre">{position}</span>
              )}
            </Case>
          )
        })}
      </div>
    </div>
  )
}

function Case({
  position,
  survole,
  onSurvol,
  onDeposer,
  children,
}: {
  position: string
  survole: boolean
  onSurvol: (actif: boolean) => void
  onDeposer: () => void
  children: React.ReactNode
}) {
  return (
    <div
      className={`case${survole ? ' case--survol' : ''}`}
      aria-label={`Position ${position}`}
      // `preventDefault` sur `dragOver` : sans lui, le navigateur **refuse** le dépôt (comportement
      // par défaut = pas de zone de drop).
      onDragOver={(e) => {
        e.preventDefault()
        onSurvol(true)
      }}
      onDragLeave={() => onSurvol(false)}
      onDrop={(e) => {
        e.preventDefault()
        onDeposer()
      }}
    >
      {children}
    </div>
  )
}

function JetonArcher({
  jeton,
  onGlisser,
}: {
  jeton: Jeton
  onGlisser: (inscriptionId: number) => void
}) {
  // Sans inscription connue (correspondance encore en chargement), le jeton n'est pas déplaçable :
  // le PUT porte l'`inscription_id`, on ne devine pas.
  const deplacable = jeton.inscriptionId !== undefined
  return (
    <span
      className={`jeton${deplacable ? '' : ' jeton--fige'}`}
      draggable={deplacable}
      title={deplacable ? 'Glisser pour déplacer' : 'Inscription introuvable — non déplaçable'}
      onDragStart={(e) => {
        if (jeton.inscriptionId === undefined) {
          e.preventDefault()
          return
        }
        e.dataTransfer.effectAllowed = 'move'
        e.dataTransfer.setData('text/plain', String(jeton.inscriptionId))
        onGlisser(jeton.inscriptionId)
      }}
    >
      {jeton.nom}
    </span>
  )
}

function Reserve({
  conflits,
  jeton,
  survole,
  setSurvol,
  onGlisser,
  onDeposer,
}: {
  conflits: Conflit[]
  jeton: (archerId: number) => Jeton
  survole: boolean
  setSurvol: (cle: string | null) => void
  onGlisser: (inscriptionId: number) => void
  onDeposer: () => void
}) {
  return (
    <div
      className={`reserve${survole ? ' reserve--survol' : ''}`}
      aria-label="Réserve (archers non placés)"
      onDragOver={(e) => {
        e.preventDefault()
        setSurvol('reserve')
      }}
      onDragLeave={() => setSurvol(null)}
      onDrop={(e) => {
        e.preventDefault()
        onDeposer()
      }}
    >
      <span className="reserve__titre">Réserve ({conflits.length})</span>
      {conflits.length === 0 ? (
        <span className="carte__etat">Aucun archer en attente.</span>
      ) : (
        <ul className="reserve__liste">
          {conflits.map((conflit) => (
            <li key={conflit.archer_id} className="reserve__item">
              <JetonArcher jeton={jeton(conflit.archer_id)} onGlisser={onGlisser} />
              <span
                className={`reserve__raison${RAISON_ANOMALIE[conflit.raison] ? ' reserve__raison--anomalie' : ''}`}
              >
                {LIBELLE_RAISON[conflit.raison]}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function nomComplet(archer: Archer): string {
  return `${archer.prenom} ${archer.nom}`.trim()
}

function messageErreur(erreur: Error): string {
  return erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
}

function MessageErreur({ erreur }: { erreur: Error | null }) {
  if (erreur === null) return null
  return (
    <p className="carte__etat carte__etat--erreur" role="alert">
      {messageErreur(erreur)}
    </p>
  )
}
