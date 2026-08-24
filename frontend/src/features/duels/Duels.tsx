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
//
// La **mise en page** est alignée sur celle du plan de cibles (E16US005) : une cible par ligne,
// couloirs alignés en colonnes, repères sous le nom, réserve en panneau collant. Le refus A11 ne
// visait que le plan de qualification, mais les deux écrans ont le même défaut, le même utilisateur
// et le même PC — arbitrage du commanditaire au cadrage du 24/08/2026.

import { useMemo, useState, type CSSProperties } from 'react'
import { ErreurApi } from '../../shared/api/client'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useArchers } from '../archers/hooks'
import { useBlasons } from '../blasons/hooks'
import { useCategories } from '../categories/hooks'
import { useClubs } from '../clubs/hooks'
import type { Archer } from '../competition/api'
import { ChoixCreneau } from '../departs/ChoixCreneau'
import { useCreneauDesDuels } from '../departs/hooks'
import { useAvancementPhases } from '../phases/hooks'
import type { CiblePlaceeDuel, Conflit, Destination, PlanDeDuels } from './api'
import {
  useDeplacerDuelliste,
  usePlacerRestantsDuels,
  usePlanDeDuels,
  useRegenererDuels,
} from './hooks'
import type { LignesDeReperes, ReferentielsDuPlan } from '../placement/presentation'
import {
  LIBELLE_RAISON,
  RAISON_ANOMALIE,
  POSITIONS,
  lignesDeReperes,
  resumeCloisonnementNonRespecte,
} from '../placement/presentation'
import { resumeAdjacenceNonGarantie } from './presentation'

export function Duels({ tournoiId }: { tournoiId: number }) {
  // Créneau **figé une fois résolu** (cf. `useCreneauDesDuels`) : recalculé à chaque rendu, il
  // suivait les changements d'état poussés par le temps réel et déplaçait l'écran tout seul.
  const { departs, liste, departId, choisir } = useCreneauDesDuels(tournoiId)
  // ⚠️ **`useAvancementPhases(departId)` et non `usePhases(tournoiId)`** (revue E01US025, axe
  // adversarial) : `GET /tournois/{id}/phases` rend le **déroulé** depuis ADR-0076, donc des `id`
  // de `deroule_etape`, alors que le plan de duels se place sur une **phase**. Les deux séquences
  // d'`id` coïncident sur un tournoi mono-départ — d'où l'invisibilité — et divergent dès le second
  // créneau : on plaçait alors les duellistes dans le tableau de l'autre départ.
  const phases = useAvancementPhases(departId)
  const [phaseId, setPhaseId] = useState<number | null>(null)

  // Le plan de duels n'a de sens que pour une phase de **tableau** (élimination directe) : on ne
  // propose que celles-là dans le sélecteur. Le serveur reste l'autorité (`phase_pas_un_tableau`
  // si l'on force une autre phase), mais restreindre la liste évite d'y arriver par mégarde.
  const tableaux = (phases.data ?? []).filter((p) => p.type === 'elimination_directe')
  // Le choix de phase est **relatif au créneau** : changer de départ rend l'ancien `phaseId`
  // étranger à la liste. Le garder afficherait le tableau de l'autre créneau — un identifiant
  // valide, donc pas la moindre erreur —, exactement le défaut qu'on vient de fermer un cran plus
  // haut. On retombe alors sur « aucune phase choisie ».
  const phaseRetenue =
    phaseId !== null && tableaux.some((phase) => phase.id === phaseId) ? phaseId : null

  return (
    <section>
      <h3 className="carte__soustitre">Plan de duels</h3>
      <ChoixCreneau departs={liste} valeur={departId} surChangement={choisir} />
      {departs.isSuccess && liste.length === 0 && (
        <p className="carte__etat">Aucun départ n’est encore défini pour ce tournoi.</p>
      )}
      {phases.isSuccess && tableaux.length === 0 && (
        <p className="carte__etat">
          Aucune phase de tableau (élimination directe) dans ce tournoi : ajoutez-en une dans «
          Phases du tournoi » avant de placer les duellistes.
        </p>
      )}
      {tableaux.length > 0 && (
        <select
          className="formulaire__champ"
          value={phaseRetenue ?? ''}
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
      {phaseRetenue !== null && (
        <PlanPhase key={phaseRetenue} tournoiId={tournoiId} phaseId={phaseRetenue} />
      )}
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
  //
  // On garde l'archer **entier** (E16US005) : le jeton porte aussi son club et sa catégorie.
  const archers = useArchers(tournoiId)
  const archerParId = useMemo(() => {
    const map = new Map<number, Archer>()
    for (const archer of archers.data ?? []) map.set(archer.id, archer)
    return map
  }, [archers.data])

  // Les trois référentiels que les repères traduisent en clair (E16US005), comme sur le plan de
  // cibles — au plus trois GET au montage, servis par le cache de 30 s quand on vient de l'atelier.
  // Le cloisonnement vaut ici aussi : c'est la même salle, réglée une fois pour le tournoi.
  const clubs = useClubs()
  const categories = useCategories(tournoiId)
  const blasons = useBlasons(tournoiId)
  const referentiels = useMemo<ReferentielsDuPlan>(
    () => ({
      clubs: new Map((clubs.data ?? []).map((club) => [club.id, club.nom])),
      categories: new Map((categories.data ?? []).map((c) => [c.id, c.libelle])),
      blasons: new Map((blasons.data ?? []).map((blason) => [blason.id, blason.nom])),
    }),
    [blasons.data, categories.data, clubs.data],
  )

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

  // `blasonId` vient du **placement** (le carton sur lequel le duelliste tire ici) ; un duelliste en
  // réserve n'en a pas encore.
  const jeton = (archerId: number, inscriptionId: number, blasonId: number | null): Jeton => {
    const archer = archerParId.get(archerId)
    return {
      nom: archer ? nomComplet(archer) : `Archer #${archerId}`,
      lignes: lignesDeReperes(archer, blasonId, referentiels),
      inscriptionId,
    }
  }

  // Nombre de colonnes de couloirs, **dérivé du plan** : les cibles n'ont pas toutes la même
  // capacité, et les aligner d'une bande à l'autre demande une grille commune — une cible à 2
  // places occupe alors les colonnes A et B, les deux suivantes restant vides. C'est le seul
  // service que rend ce calcul, et c'est un vrai service.
  //
  // ⚠️ Le `Math.min` n'est pas décoratif : sans lui, une capacité serveur > 4 ouvrirait N colonnes
  // sur **toutes** les bandes du plan, en n'en remplissant que 4 (`POSITIONS.slice`) — donc une
  // colonne fantôme qui rétrécit les autres. La grille ne « suit » pas un délestage du plafond :
  // c'est `POSITIONS` qui le porte (`DETTE-010`), et le `Math.min` fait que le rendu reste cohérent
  // en attendant E01US019.
  const couloirs = Math.max(
    1,
    ...plan.cibles.map((cible) => Math.min(cible.capacite, POSITIONS.length)),
  )

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

      {/* Le plan et son puits (E16US005) : deux colonnes, la reserve **collante** a droite. */}
      <div className="placement__plan">
        <div className="placement__cibles" style={{ '--couloirs': couloirs } as CSSProperties}>
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
    </div>
  )
}

// `reperes` : club, catégorie, blason déjà traduits en clair (cf. `placement/presentation.ts`).
//
// DETTE-085 : ce type et les quatre composants qui suivent (`Cible`, `Case`, `JetonArcher`,
// `Reserve`) sont la **copie** de ceux de `placement/Placement.tsx`, dont cet écran a été cloné à
// E03US009. E16US005 a dû appliquer deux fois le même changement de mise en page — c'est la preuve
// qui manquait au registre. Remède prévu : les remonter dans `shared/plan-de-cibles/`, badges
// passés en `ReactNode` (US de rangement dédiée, avec DETTE-083).
type Jeton = { nom: string; lignes: LignesDeReperes; inscriptionId: number }

function Cible({
  cible,
  jeton,
  survol,
  setSurvol,
  onGlisser,
  onDeposer,
}: {
  cible: CiblePlaceeDuel
  jeton: (archerId: number, inscriptionId: number, blasonId: number | null) => Jeton
  survol: string | null
  setSurvol: (cle: string | null) => void
  onGlisser: (inscriptionId: number) => void
  onDeposer: (destination: Destination) => void
}) {
  const positions = POSITIONS.slice(0, cible.capacite)

  return (
    <div className="cible">
      {/* En-tête de la bande (E16US005) : numéro et signaux à gauche, couloirs sur le reste. */}
      <div className="cible__entete">
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
      </div>
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
                  {/* La lettre du couloir sur une case **occupée** (E16US005) : le placement la
                      rendait déjà (E03US011), pas les duels — or la fiche de recette annonce
                      « exactement la même présentation ». En bandes, c'est elle qui rattache un
                      jeton à sa colonne quand les capacités diffèrent d'une cible à l'autre. */}
                  <span className="case__position">{position}</span>
                  <JetonArcher
                    jeton={jeton(place.archer_id, place.inscription_id, place.blason_id)}
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
      // Les repères sont **tronqués** dans une case (`.cible .jeton__reperes`) : le titre porte le
      // texte entier, sinon un couloir étroit les rendrait illisibles sans recours.
      // ⚠️ L'affordance du geste est **toujours** présente, jamais remplacée : la version
      // conditionnelle la faisait disparaître dès qu'un archer avait un club — c'est-à-dire
      // toujours —, sur un écran dont le glisser-déposer est le geste central. Deux jetons voisins
      // n'avaient alors pas le même contrat d'infobulle.
      title={[jeton.lignes.club, ...jeton.lignes.cloisonnement, 'glisser pour déplacer']
        .filter((part): part is string => part !== null)
        .join(' · ')}
      onDragStart={(e) => {
        e.dataTransfer.effectAllowed = 'move'
        e.dataTransfer.setData('text/plain', String(jeton.inscriptionId))
        onGlisser(jeton.inscriptionId)
      }}
    >
      <span className="jeton__nom">{jeton.nom}</span>
      {/* Les repères (E16US005) : ce sur quoi portent les deux badges de la cible. **Deux lignes de
          nature différente**, et c'est ce qui décide de ce qu'on lit — le club est un bloc
          insécable qu'on tronque, « catégorie · blason » se coupe aux espaces et ne doit **pas**
          l'être : sous les réglages `blason` et `blason_et_categorie`, le blason est le seul repère
          qui explique le cloisonnement, et c'est le dernier de la chaîne. Le découpage vient de
          `lignesDeReperes` et non d'un index : rien ne garantit que le club soit le premier élément
          d'une liste plate (les trois référentiels sont trois requêtes). */}
      {jeton.lignes.club !== null && (
        <span className="jeton__reperes jeton__reperes--club">{jeton.lignes.club}</span>
      )}
      {jeton.lignes.cloisonnement.length > 0 && (
        <span className="jeton__reperes">{jeton.lignes.cloisonnement.join(' · ')}</span>
      )}
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
  jeton: (archerId: number, inscriptionId: number, blasonId: number | null) => Jeton
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
              {/* Pas de blason en réserve : le duelliste n'est posé nulle part. */}
              <JetonArcher
                jeton={jeton(conflit.archer_id, conflit.inscription_id, null)}
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

// DETTE-050 : copie verbatim de `shared/ui/texteErreur` (l'autre est dans
// `features/placement/Placement.tsx`). Le narrowing est correct ici — c'est sa **duplication**
// qui est la dette : **cinq** sites portent cet invariant — ce module, les deux copies verbatim,
// et deux encodages inline (`supervision/Supervision.tsx`, `supervision/PiloterEcrans.tsx`) —
// dont un seul est le point de vérité. Une résorption qui ne viserait que « les deux helpers
// dupliqués » laisserait les deux inline derrière elle.
function messageErreur(erreur: Error): string {
  return erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
}
