// Écran d'ajustement du placement (E03US004, ADR-0024) — réservé à l'admin (monté sous `estAdmin`).
//
// On choisit un départ (créneau), puis on ajuste son plan de cibles au **glisser-déposer** : on
// glisse un jeton d'archer d'une cible à l'autre, vers une case libre (déplacement) ou occupée
// (échange), ou vers la **réserve** (mise à l'écart). Le serveur reste l'autorité : chaque geste est
// un PUT, et un refus (`409 deplacement_invalide`) laisse le plan inchangé — on affiche l'alerte et
// on refetch. Drag & drop **HTML5 natif** (à la souris, écran admin sur PC) : aucune dépendance.

import { useMemo, useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import { ConfirmationChiffree } from '../../shared/confirmation/ConfirmationChiffree'
import { useArchers } from '../archers/hooks'
import type { Archer } from '../competition/api'
import { useDeparts } from '../departs/hooks'
import type {
  CiblePlacee,
  Conflit,
  Destination,
  ImpactRegeneration,
  PlanDeCibles,
  RaisonConflit,
} from './api'
import {
  useDeplacer,
  useImpactRegeneration,
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
  // Noms des archers (une requête, partagée). L'`inscription_id` — cible du déplacement — vient
  // directement du plan (chaque placement et chaque conflit le porte), rien à reconstituer.
  const archers = useArchers(tournoiId)
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
  // L'impact n'est calculé (serveur) qu'à l'ouverture du panneau de confirmation (E12US007) : il
  // chiffre l'alerte et dit si un mot est à taper (niveau massif = des scores existent déjà).
  const impact = useImpactRegeneration(tournoiId, departId, confirmationAnnulation)

  const deposer = (destination: Destination) => {
    setSurvol(null)
    if (inscriptionGlissee === null) return
    deplacer.mutate({ inscriptionId: inscriptionGlissee, destination })
    setInscriptionGlissee(null)
  }

  // « Vide » = aucune cible remplie. On l'interprète comme « plan jamais généré » (la lecture ne
  // génère pas, E03US004) → bouton « Générer » ; sinon « Annuler les modifications » (même endpoint,
  // mais l'annulation **écrase** les ajustements → confirmation).
  // Limite connue (revue D) : un plan **vidé à la main** (tous les archers en réserve) est
  // indiscernable d'un plan jamais généré (aucune affectation persistée dans les deux cas), donc
  // « Générer » y régénère sans confirmation. Effet **borné et réversible** (auto déterministe), on
  // l'assume plutôt que de persister un drapeau « généré ».
  const planVide = plan.cibles.every((cible) => cible.placements.length === 0)
  const planPret = plan.conflits.length === 0 && !planVide

  const jeton = (archerId: number, inscriptionId: number): Jeton => ({
    nom: nomParArcher.get(archerId) ?? `Archer #${archerId}`,
    inscriptionId,
  })

  return (
    <div className="placement">
      <div className="placement__barre">
        {planVide ? (
          <button
            type="button"
            disabled={regenerer.isPending}
            onClick={() => regenerer.mutate(false)}
          >
            Générer le plan
          </button>
        ) : (
          !confirmationAnnulation && (
            <button
              type="button"
              className="bouton--discret"
              onClick={() => setConfirmationAnnulation(true)}
            >
              Annuler les modifications
            </button>
          )
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

      {/* Confirmation par calcul d'impact (E12US007, ADR-0040) : l'alerte est **chiffrée** et, si des
          scores existent déjà (niveau massif), exige de taper REPLACER. */}
      {confirmationAnnulation &&
        (impact.isPending ? (
          <p className="carte__etat">Calcul de l'impact…</p>
        ) : impact.isError ? (
          <MessageErreur erreur={impact.error} />
        ) : impact.data ? (
          <ConfirmationChiffree
            titre="Régénérer le plan de cibles"
            motRequis={impact.data.niveau === 'massif' ? 'REPLACER' : undefined}
            libelleConfirmer={
              impact.data.niveau === 'massif'
                ? 'Régénérer le plan'
                : 'Confirmer — écraser les ajustements'
            }
            enCours={regenerer.isPending}
            onConfirmer={() =>
              regenerer.mutate(true, { onSuccess: () => setConfirmationAnnulation(false) })
            }
            onAnnuler={() => setConfirmationAnnulation(false)}
          >
            <MessageImpact impact={impact.data} />
          </ConfirmationChiffree>
        ) : null)}

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

type Jeton = { nom: string; inscriptionId: number }

function Cible({
  cible,
  jeton,
  survol,
  setSurvol,
  onGlisser,
  onDeposer,
}: {
  cible: CiblePlacee
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
              <JetonArcher
                jeton={jeton(conflit.archer_id, conflit.inscription_id)}
                onGlisser={onGlisser}
              />
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

// Corps chiffré de l'alerte de régénération (E12US007) : dit **ce qui est en jeu**, jamais un « Êtes-
// vous sûr ? » creux. Le niveau massif rappelle que les scores sont **conservés** (la régénération ne
// réécrit que le placement) — l'archer bouge de cible, ses flèches le suivent.
function MessageImpact({ impact }: { impact: ImpactRegeneration }) {
  const archers = `${impact.archers_deplaces} archer${impact.archers_deplaces > 1 ? 's' : ''}`
  if (impact.niveau === 'massif') {
    const cibles = `${impact.cibles_avec_scores} cible${impact.cibles_avec_scores > 1 ? 's' : ''}`
    return (
      <p>
        {archers} vont être replacés. {cibles} ont déjà des scores : ils seront{' '}
        <strong>conservés</strong>.
      </p>
    )
  }
  return (
    <p>{archers} vont être replacés (aucun score enregistré ; vos ajustements seront écrasés).</p>
  )
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
