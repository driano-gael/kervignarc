// Écran d'ajustement du placement (E03US004, ADR-0024) — réservé à l'admin (monté sous `estAdmin`).
//
// On choisit un départ (créneau), puis on ajuste son plan de cibles au **glisser-déposer** : on
// glisse un jeton d'archer d'une cible à l'autre, vers une case libre (déplacement) ou occupée
// (échange), ou vers la **réserve** (mise à l'écart). Le serveur reste l'autorité : chaque geste est
// un PUT, et un refus (`409 deplacement_invalide`) laisse le plan inchangé — on affiche l'alerte et
// on refetch. Drag & drop **HTML5 natif** (à la souris, écran admin sur PC) : aucune dépendance.

import { useMemo, useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { ConfirmationChiffree } from '../../shared/confirmation/ConfirmationChiffree'
import { useArchers } from '../archers/hooks'
import type { Archer } from '../competition/api'
import { useDeparts } from '../departs/hooks'
import type {
  CiblePlacee,
  Cloisonnement,
  Conflit,
  Destination,
  ImpactRegeneration,
  PlanDeCibles,
} from './api'
import {
  useCloisonnement,
  useDeplacer,
  useImpactRegeneration,
  usePlacerRestants,
  usePlanDeCibles,
  useRegenerer,
  useReglerCloisonnement,
} from './hooks'
import {
  LIBELLE_CLOISONNEMENT,
  LIBELLE_RAISON,
  RAISON_ANOMALIE,
  VALEURS_CLOISONNEMENT,
  resumeCloisonnementNonRespecte,
  resumeMixiteNonGarantie,
} from './presentation'

// Les positions d'une cible sont des lettres ; une cible de capacité N expose les N premières.
const POSITIONS = ['A', 'B', 'C', 'D']

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
      <ReglageCloisonnement tournoiId={tournoiId} />
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
              {` — ${depart.horaire}`}
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

// Réglage de cloisonnement du **tournoi** (E03US007, RG-4) : posé au-dessus du choix de départ,
// parce qu'il ne dépend pas du créneau — il vaut pour tous, et pour le plan de duels.
//
// Aucun état local : la valeur affichée est **celle du serveur** (`select` contrôlé par la query).
// Un état local synchronisé par `useEffect` afficherait un réglage que le serveur n'a pas encore
// accepté — exactement le défaut relevé en revue d'E06US006 (état dérivé d'une prop qui diverge).
function ReglageCloisonnement({ tournoiId }: { tournoiId: number }) {
  const reglage = useCloisonnement(tournoiId)
  const regler = useReglerCloisonnement(tournoiId)
  const valeur = reglage.data?.cloisonnement ?? 'aucun'

  return (
    <div className="placement__reglage">
      <label className="placement__reglage-libelle" htmlFor="cloisonnement">
        Cloisonnement des cibles
      </label>
      <select
        id="cloisonnement"
        className="formulaire__champ"
        value={valeur}
        // `isPending` sur la lecture **et** l'écriture : tant que le serveur n'a pas répondu, le
        // réglage affiché n'est pas encore une vérité — on ne laisse pas empiler les changements.
        disabled={reglage.isPending || reglage.isError || regler.isPending}
        onChange={(e) => regler.mutate(e.target.value as Cloisonnement)}
      >
        {VALEURS_CLOISONNEMENT.map((option) => (
          <option key={option} value={option}>
            {LIBELLE_CLOISONNEMENT[option]}
          </option>
        ))}
      </select>
      <p className="carte__etat">
        Le placement automatique ne mêlera plus sur une même cible ce que ce réglage sépare. Changer
        ce réglage <strong>ne déplace personne</strong> : il s'applique à la prochaine génération et
        aux déplacements à la main.
      </p>
      <MessageErreur erreur={reglage.error} />
      <MessageErreur erreur={regler.error} />
    </div>
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
  // Compteurs pour le retour de génération (E03US011) : combien d'archers posés, combien en réserve.
  // Ils alimentent la confirmation qui suit un clic sur « Générer » — sans quoi une génération qui
  // aboutit à un plan vide (aucun inscrit) ou à des archers en réserve **paraît muette**.
  const nbPlaces = plan.cibles.reduce((n, cible) => n + cible.placements.length, 0)
  const nbReserve = plan.conflits.length
  // Avertissement d'équité (E03US006, RG-3) : cibles où la mixité ≥ 2 clubs n'est pas garantie.
  // `null` si tout est mixé → aucune bannière. C'est un signal, pas un blocage (l'admin ajuste).
  const resumeMixite = resumeMixiteNonGarantie(plan.cibles)
  // Cibles qui violent le cloisonnement demandé (E03US007) — plan antérieur au réglage.
  const resumeCloisonnement = resumeCloisonnementNonRespecte(plan.cibles)

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
            {regenerer.isPending ? 'Génération…' : 'Générer le plan'}
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
          scores existent déjà (niveau massif), exige de taper REPLACER. Un bouton « Annuler » ferme
          le panneau **dans tous les états** (calcul en cours ou en échec compris), sinon un GET
          d'impact en échec — plausible sur le LAN — piégerait l'admin sans issue. */}
      {confirmationAnnulation &&
        (impact.isPending || impact.isError ? (
          <div className="confirmation" role="group" aria-label="Régénérer le plan de cibles">
            {impact.isError ? (
              <MessageErreur erreur={impact.error} />
            ) : (
              <p className="carte__etat">Calcul de l'impact…</p>
            )}
            <div className="confirmation__actions">
              <button
                type="button"
                className="bouton--discret"
                onClick={() => setConfirmationAnnulation(false)}
              >
                Annuler
              </button>
            </div>
          </div>
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
            // On n'envoie `confirme=true` que pour le niveau **massif** (que le front vient de
            // montrer avec le mot REPLACER). Si un score est validé pendant que le panneau est
            // ouvert (course confirmation→massif), le front envoie encore `false` : le serveur
            // recalcule massif, refuse (409), et le panneau rebascule pour réclamer REPLACER — le
            // geste délibéré redevient **impossible par réflexe** (CA), sans coupler le serveur à
            // la copie d'UI (ADR-0040 §4).
            onConfirmer={() =>
              regenerer.mutate(impact.data.niveau === 'massif', {
                onSuccess: () => setConfirmationAnnulation(false),
              })
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

      {/* Retour de génération (E03US011) : après un « Générer » réussi, on **confirme** le résultat —
          sinon une génération qui n'aboutit à rien (plan vide) ou laisse des archers en réserve
          paraît muette. Le cas « tous placés » est déjà couvert par `planPret` ci-dessous : on ne
          double pas la ligne verte (`!planPret`). `isSuccess` couvre aussi « annuler les
          modifications » (même mutation). Erreur et « en cours » sont pris ailleurs (MessageErreur,
          libellé du bouton).
          Ton **neutre** (`carte__etat`), pas vert `placement__pret` : le vert « succès » reste
          réservé à « tous placés ». Un reliquat en réserve peut cacher de **vraies anomalies**
          (`sans_blason` / `non_place`, ambre DV-03) — l'annoncer en vert serait trompeur ; l'ambre
          des anomalies est déjà porté par la réserve et sa bannière en dessous. */}
      {regenerer.isSuccess && !planPret && (
        <p className="carte__etat" role="status">
          {nbPlaces === 0 && nbReserve === 0
            ? 'Plan généré : aucun archer à placer sur ce départ.'
            : `Plan généré : ${nbPlaces} placé${nbPlaces > 1 ? 's' : ''}${
                nbReserve > 0 ? `, ${nbReserve} en réserve` : ''
              }.`}
        </p>
      )}

      {planPret && (
        <p className="placement__pret" role="status">
          Plan prêt : tous les archers sont placés.
        </p>
      )}

      {/* Mixité de club non garantie (E03US006, RG-3) : bannière **ambre** (DV-03), jamais rouge —
          l'objectif « ≥ 2 clubs par cible » n'est pas atteignable partout (un seul club, ou club
          inconnu). Signal, pas erreur : l'admin peut ajuster à la main. */}
      {resumeMixite && (
        <p className="placement__mixite" role="status">
          {resumeMixite}
        </p>
      )}

      {/* Cloisonnement non respecté (E03US007) : même registre **ambre** (DV-03) — signal, pas
          erreur. Il ne peut apparaître que sur un plan posé **avant** l'activation du réglage ;
          le message dit donc quoi faire (régénérer ou déplacer), sinon l'admin voit un reproche
          sans issue. */}
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
      {/* Objectif de mixité ≥ 2 clubs non atteint sur cette cible (E03US006) : badge ambre discret,
          l'admin décide s'il ajuste. Pas de badge quand la mixité est garantie ou sans objet. */}
      {cible.mixite_non_garantie && (
        <span className="cible__mixite">mixité de club non garantie</span>
      )}
      {/* Cette cible mêle ce que le réglage sépare (E03US007) : badge ambre, même registre que la
          mixité. Le placement auto ne peut pas la produire — c'est un plan à régénérer. */}
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
                <>
                  {/* Position (A..D) visible côté admin (E03US011), comme côté public : la lettre
                      n'apparaissait que sur les cases **libres** — un archer posé masquait la
                      sienne. Badge accent, même parti pris que `plan-public__position`. */}
                  <span className="case__position">{position}</span>
                  <JetonArcher
                    jeton={jeton(place.archer_id, place.inscription_id)}
                    onGlisser={onGlisser}
                  />
                </>
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

// Corps chiffré de l'alerte de régénération (E12US007) : dit **ce qui est en jeu**, jamais un « Êtes-
// vous sûr ? » creux. Le niveau massif rappelle que les scores sont **conservés** (la régénération ne
// réécrit que le placement) — l'archer bouge de cible, ses flèches le suivent.
function MessageImpact({ impact }: { impact: ImpactRegeneration }) {
  // Accord au nombre : `massif` peut valoir exactement 1 archer / 1 cible (un seul placé, scoré) —
  // « 1 archer va » / « 1 cible a », jamais le pluriel systématique.
  const plurielArchers = impact.archers_deplaces > 1
  const archers = `${impact.archers_deplaces} archer${plurielArchers ? 's' : ''}`
  const replaces = `${plurielArchers ? 'vont' : 'va'} être replacé${plurielArchers ? 's' : ''}`
  if (impact.niveau === 'massif') {
    const plurielCibles = impact.cibles_avec_scores > 1
    const cibles = `${impact.cibles_avec_scores} cible${plurielCibles ? 's' : ''}`
    return (
      <p>
        {archers} {replaces}. {cibles} {plurielCibles ? 'ont' : 'a'} déjà des scores : ils seront{' '}
        <strong>conservés</strong>.
      </p>
    )
  }
  return (
    <p>
      {archers} {replaces} (aucun score enregistré ; vos ajustements seront écrasés).
    </p>
  )
}

function messageErreur(erreur: Error): string {
  return erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
}
