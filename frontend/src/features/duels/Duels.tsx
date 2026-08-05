// Écran d'ajustement du plan de duels (E03US009, ADR-0048) — réservé à l'admin (monté sous
// `estAdmin`).
//
// On choisit une **phase de tableau** (élimination directe), puis on ajuste le placement de ses
// duellistes au **glisser-déposer** : on glisse un jeton d'une cible à l'autre, vers une case libre
// (déplacement) ou occupée (échange), ou vers la **réserve** (mise à l'écart). Le serveur reste
// l'autorité : chaque geste est un PUT, et un refus (`409 deplacement_invalide`) laisse le plan
// inchangé — on affiche l'alerte et on refetch. Drag & drop **HTML5 natif** : aucune dépendance.
//
// Jumeau de `placement/Placement.tsx` (plan de cibles de qualification), à deux différences près :
//  - le signal d'équité est l'**adjacence** (adversaires côte à côte), pas la mixité de club ;
//    en revanche le **cloisonnement** (E03US007) vaut ici aussi : c'est la même salle, réglée une
//    fois pour le tournoi — d'où les libellés de réserve et la bannière importés de `placement` ;
//  - **aucune** confirmation d'impact (E12US007) : la régénération est **directe** (ADR-0048).

import { useMemo, useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useArchers } from '../archers/hooks'
import type { Archer } from '../competition/api'
import { usePhases } from '../phases/hooks'
import type { CiblePlaceeDuel, Conflit, Destination, PlanDeDuels } from './api'
import {
  useDeplacerDuelliste,
  usePlacerRestantsDuels,
  usePlanDeDuels,
  useRegenererDuels,
} from './hooks'
import {
  LIBELLE_RAISON,
  RAISON_ANOMALIE,
  resumeCloisonnementNonRespecte,
} from '../placement/presentation'
import { resumeAdjacenceNonGarantie } from './presentation'

// Les positions d'une cible sont des lettres ; une cible de capacité N expose les N premières.
const POSITIONS = ['A', 'B', 'C', 'D']

export function Duels({ tournoiId }: { tournoiId: number }) {
  const phases = usePhases(tournoiId)
  const [phaseId, setPhaseId] = useState<number | null>(null)

  // Le plan de duels n'a de sens que pour une phase de **tableau** (élimination directe) : on ne
  // propose que celles-là dans le sélecteur. Le serveur reste l'autorité (`phase_pas_un_tableau`
  // si l'on force une autre phase), mais restreindre la liste évite d'y arriver par mégarde.
  const tableaux = (phases.data ?? []).filter((p) => p.type === 'elimination_directe')

  return (
    <section>
      <h3 className="carte__soustitre">Plan de duels</h3>
      {phases.isSuccess && tableaux.length === 0 && (
        <p className="carte__etat">
          Aucune phase de tableau (élimination directe) dans ce tournoi : ajoutez-en une dans «
          Phases (format) » avant de placer les duellistes.
        </p>
      )}
      {tableaux.length > 0 && (
        <select
          className="formulaire__champ"
          value={phaseId ?? ''}
          onChange={(e) => setPhaseId(e.target.value === '' ? null : Number(e.target.value))}
          aria-label="Phase de tableau à placer"
        >
          <option value="">Choisir une phase…</option>
          {tableaux.map((phase) => (
            <option key={phase.id} value={phase.id}>
              Phase {phase.ordre} — élimination directe
            </option>
          ))}
        </select>
      )}
      {/* `key` sur la phase : changer de phase **remonte** le sous-arbre, ce qui réinitialise l'état
          de drag sans le synchroniser à la main. */}
      {phaseId !== null && <PlanPhase key={phaseId} tournoiId={tournoiId} phaseId={phaseId} />}
    </section>
  )
}

function PlanPhase({ tournoiId, phaseId }: { tournoiId: number; phaseId: number }) {
  const plan = usePlanDeDuels(tournoiId, phaseId)

  if (plan.isPending) return <p className="carte__etat">Chargement du plan…</p>
  if (plan.isError) {
    return (
      <div>
        <MessageErreur erreur={plan.error} />
        <p className="carte__etat">
          Un plan de duels suppose une phase de tableau (élimination directe) dont les duellistes
          sont connus (peuplement de la phase).
        </p>
      </div>
    )
  }
  return <PlanCharge tournoiId={tournoiId} phaseId={phaseId} plan={plan.data} />
}

function PlanCharge({
  tournoiId,
  phaseId,
  plan,
}: {
  tournoiId: number
  phaseId: number
  plan: PlanDeDuels
}) {
  // Noms des archers (une requête, partagée). L'`inscription_id` — cible du déplacement — vient
  // directement du plan (chaque placement et chaque conflit le porte), rien à reconstituer.
  const archers = useArchers(tournoiId)
  const nomParArcher = useMemo(() => {
    const map = new Map<number, string>()
    for (const archer of archers.data ?? []) map.set(archer.id, nomComplet(archer))
    return map
  }, [archers.data])

  const regenerer = useRegenererDuels(tournoiId, phaseId)
  const deplacer = useDeplacerDuelliste(tournoiId, phaseId)
  const placerRestants = usePlacerRestantsDuels(tournoiId, phaseId)

  // Inscription en cours de glissement + case survolée (surbrillance). L'état vit ici : les cases et
  // la réserve sont des cibles de dépôt qui déclenchent le PUT via `deposer`.
  const [inscriptionGlissee, setInscriptionGlissee] = useState<number | null>(null)
  const [survol, setSurvol] = useState<string | null>(null)

  const deposer = (destination: Destination) => {
    setSurvol(null)
    if (inscriptionGlissee === null) return
    deplacer.mutate({ inscriptionId: inscriptionGlissee, destination })
    setInscriptionGlissee(null)
  }

  // « Vide » = aucune cible remplie. On l'interprète comme « plan jamais généré » → bouton
  // « Générer » ; sinon « Régénérer » (même endpoint, l'auto écrase les ajustements). Contrairement
  // à la qualification (E12US007), **aucune confirmation** : la régénération est directe (ADR-0048).
  const planVide = plan.cibles.every((cible) => cible.placements.length === 0)
  const planPret = plan.conflits.length === 0 && !planVide
  // Avertissement d'organisation (E03US009) : duels dont les adversaires ne sont pas côte à côte.
  // `null` si tout est adjacent → aucune bannière. Signal, pas blocage (l'admin ajuste).
  const resumeAdjacence = resumeAdjacenceNonGarantie(plan)
  // Cibles du plan de duels qui violent le cloisonnement demandé (E03US007).
  const resumeCloisonnement = resumeCloisonnementNonRespecte(plan.cibles)

  const jeton = (archerId: number, inscriptionId: number): Jeton => ({
    nom: nomParArcher.get(archerId) ?? `Archer #${archerId}`,
    inscriptionId,
  })

  return (
    <div className="placement">
      <div className="placement__barre">
        <button
          type="button"
          className={planVide ? undefined : 'bouton--discret'}
          disabled={regenerer.isPending}
          onClick={() => regenerer.mutate()}
        >
          {planVide ? 'Générer le plan' : 'Régénérer (annuler les modifications)'}
        </button>
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
          Plan prêt : tous les duellistes sont placés.
        </p>
      )}

      {/* Adjacence non garantie (E03US009) : bannière **ambre** (DV-03), jamais rouge — au moins un
          duel n'est pas côte à côte. Signal, pas erreur : l'admin peut ajuster à la main. */}
      {resumeAdjacence && (
        <p className="placement__mixite" role="status">
          {resumeAdjacence}
        </p>
      )}

      {/* Cloisonnement non respecté (E03US007) : plan de duels posé avant l'activation du réglage.
          Même registre ambre, même message que sur le plan de cibles — un seul énoncé. */}
      {resumeCloisonnement && (
        <p className="placement__mixite" role="status">
          {resumeCloisonnement}
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

type Jeton = { nom: string; inscriptionId: number }

function Cible({
  cible,
  jeton,
  survol,
  setSurvol,
  onGlisser,
  onDeposer,
}: {
  cible: CiblePlaceeDuel
  jeton: (archerId: number, inscriptionId: number) => Jeton
  survol: string | null
  setSurvol: (cle: string | null) => void
  onGlisser: (inscriptionId: number) => void
  onDeposer: (destination: Destination) => void
}) {
  const positions = POSITIONS.slice(0, cible.capacite)

  return (
    <div className="cible">
      <span className="cible__titre">Cible {cible.index}</span>
      {/* Adjacence non garantie sur cette cible (E03US009) : badge ambre discret, l'admin décide
          s'il ajuste. Pas de badge quand les duels sont bien côte à côte. */}
      {cible.adjacence_non_garantie && (
        <span className="cible__adjacence">duel non côte à côte</span>
      )}
      {/* Cette cible mêle ce que le cloisonnement du tournoi sépare (E03US007) : plan posé avant
          l'activation du réglage — le placement auto ne peut pas le produire. Même badge ambre
          qu'en qualification. */}
      {cible.cloisonnement_non_respecte && (
        <span className="cible__mixite">cloisonnement non respecté</span>
      )}
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
                <JetonArcher
                  jeton={jeton(place.archer_id, place.inscription_id)}
                  onGlisser={onGlisser}
                />
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
      aria-label={`Couloir de tir ${position}`}
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
  return (
    <span
      className="jeton"
      draggable
      title="Glisser pour déplacer"
      onDragStart={(e) => {
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
  jeton: (archerId: number, inscriptionId: number) => Jeton
  survole: boolean
  setSurvol: (cle: string | null) => void
  onGlisser: (inscriptionId: number) => void
  onDeposer: () => void
}) {
  return (
    <div
      className={`reserve${survole ? ' reserve--survol' : ''}`}
      aria-label="Réserve (duellistes non placés)"
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
        <span className="carte__etat">Aucun duelliste en attente.</span>
      ) : (
        <ul className="reserve__liste">
          {conflits.map((conflit) => (
            <li key={conflit.archer_id} className="reserve__item">
              <JetonArcher
                jeton={jeton(conflit.archer_id, conflit.inscription_id)}
                onGlisser={onGlisser}
              />
              <span
                className={`reserve__raison${RAISON_ANOMALIE[conflit.raison] ? ' reserve__raison--anomalie' : ''}`}
              >
                {/* Repli : mutualiser le vocabulaire supprime la recopie **entre écrans**, pas
                    la divergence **front ↔ serveur** — c'est pourtant elle qui a produit le défaut
                    d'E03US007. Une raison inconnue s'affiche telle quelle plutôt qu'en blanc. */}
                {LIBELLE_RAISON[conflit.raison] ?? conflit.raison}
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
