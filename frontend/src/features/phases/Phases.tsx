// Séquence de phases d'un tournoi (E05US001, ADR-0045) — réservée à l'admin (montée sous `estAdmin`).
//
// Compose et fait vivre la suite ordonnée des phases : ajouter (élimination directe / placement),
// typer, déclarer une **source** de peuplement (les rangs [a..b] d'une phase antérieure) et un
// **effectif**, réordonner (monter/descendre), supprimer, et piloter le **cycle de vie** de chaque
// phase (à venir → en cours ⇄ en pause → terminée). La cohérence (source vide / rangs inexistants /
// effectif incompatible) est vérifiée par le serveur : ses refus s'affichent tels quels (422/409).
//
// La phase de **qualification** (créée via l'écran « Barème & validation ») apparaît dans la liste
// mais ne s'ajoute pas ici : ce sont les phases du **moteur d'élimination** qu'on compose.
//
// Une phase porte désormais **plusieurs** prélèvements, de natures variées (E05US010). Cet écran
// les **affiche** tous mais n'en **édite** qu'un seul, « par rangs » — la composition riche est
// l'objet d'E01US024. Toute phase hors de ce cas est donc affichée en lecture (`editableIci`) :
// la soumettre avec ce formulaire écraserait sa composition sans le dire.

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import type {
  ConfigPhase,
  Phase,
  SourcePhase,
  StatutPhase,
  TransitionPhase,
  TypePhase,
} from './api'
import {
  useAjouterPhase,
  useChangerStatutPhase,
  useModifierPhase,
  usePhases,
  useReordonnerPhases,
  useSupprimerPhase,
} from './hooks'
import { ordreApresDeplacement, type Direction } from './ordre'
import { decrireSources, editableIci } from './source'

const LIBELLE_TYPE: Record<TypePhase, string> = {
  qualification: 'Qualification',
  elimination_directe: 'Élimination directe',
  placement: 'Placement',
}

// Types composables ici (la qualification se règle via le barème). Le catalogue s'élargira avec les
// US qui implémentent les autres formats (ADR-0045 §2).
const TYPES_AJOUTABLES: TypePhase[] = ['elimination_directe', 'placement']

const LIBELLE_STATUT: Record<StatutPhase, string> = {
  a_venir: 'À venir',
  en_cours: 'En cours',
  en_pause: 'En pause',
  terminee: 'Terminée',
}

// Transitions offertes selon le statut courant (ADR-0045 §1). Le serveur reste l'autorité (409 si
// l'état a changé entre l'affichage et le clic).
const TRANSITIONS: Record<StatutPhase, { transition: TransitionPhase; libelle: string }[]> = {
  a_venir: [{ transition: 'demarrer', libelle: 'Démarrer' }],
  en_cours: [
    { transition: 'mettre_en_pause', libelle: 'Mettre en pause' },
    { transition: 'terminer', libelle: 'Terminer' },
  ],
  en_pause: [{ transition: 'reprendre', libelle: 'Reprendre' }],
  terminee: [],
}

export function Phases({ tournoiId }: { tournoiId: number }) {
  const phases = usePhases(tournoiId)
  const liste = phases.data ?? []

  return (
    <section>
      <h3 className="carte__soustitre">Phases (format du tournoi)</h3>
      <p className="carte__etat">
        Composez la suite des phases après la qualification (élimination directe, placement). La
        qualification se règle dans « Barème &amp; validation ».
      </p>
      <FormulairePhase tournoiId={tournoiId} phases={liste} />
      {phases.isError && <MessageErreur erreur={phases.error} />}
      {liste.length > 0 && (
        <ol className="liste-phases">
          {liste.map((phase, index) => (
            <LignePhase
              key={phase.id}
              tournoiId={tournoiId}
              phase={phase}
              phases={liste}
              premier={index === 0}
              dernier={index === liste.length - 1}
            />
          ))}
        </ol>
      )}
    </section>
  )
}

function BadgePhase({ statut }: { statut: StatutPhase }) {
  return (
    <span className={`badge badge--${statut.replace('_', '-')}`}>{LIBELLE_STATUT[statut]}</span>
  )
}

function LignePhase({
  tournoiId,
  phase,
  phases,
  premier,
  dernier,
}: {
  tournoiId: number
  phase: Phase
  phases: Phase[]
  premier: boolean
  dernier: boolean
}) {
  const [edition, setEdition] = useState(false)
  const [confirmationSuppression, setConfirmationSuppression] = useState(false)
  const reordonner = useReordonnerPhases(tournoiId)
  const supprimer = useSupprimerPhase(tournoiId)
  const changerStatut = useChangerStatutPhase(tournoiId)

  const deplacer = (direction: Direction) => {
    const ordre = ordreApresDeplacement(phases, phase.id, direction)
    if (ordre !== null) reordonner.mutate(ordre)
  }

  // La qualification se gère sur l'écran « Barème & validation » : on n'offre pas ici de l'éditer ni
  // de la supprimer (ce serait perdre son barème par surprise). Elle reste réordonnable et pilotable.
  const gereeAilleurs = phase.type === 'qualification'

  if (edition) {
    return (
      <li className="phase">
        <FormulairePhase
          tournoiId={tournoiId}
          phases={phases}
          phase={phase}
          onTermine={() => setEdition(false)}
        />
      </li>
    )
  }

  return (
    <li className="phase">
      <div className="phase__ligne">
        <span className="phase__ordre">{phase.ordre}</span>
        <span className="phase__type">{LIBELLE_TYPE[phase.type]}</span>
        <BadgePhase statut={phase.statut} />
        <span className="phase__details">
          {decrireSources(phase.sources)}
          {phase.effectif !== null && ` · ${phase.effectif} participants`}
        </span>
      </div>
      <div className="phase__actions">
        <button
          type="button"
          className="bouton--discret"
          disabled={premier || reordonner.isPending}
          onClick={() => deplacer('monter')}
          aria-label={`Monter la phase ${phase.ordre}`}
        >
          ↑
        </button>
        <button
          type="button"
          className="bouton--discret"
          disabled={dernier || reordonner.isPending}
          onClick={() => deplacer('descendre')}
          aria-label={`Descendre la phase ${phase.ordre}`}
        >
          ↓
        </button>
        {TRANSITIONS[phase.statut].map((action) => (
          <button
            key={action.transition}
            type="button"
            className="bouton--discret"
            disabled={changerStatut.isPending}
            onClick={() =>
              changerStatut.mutate({ phaseId: phase.id, transition: action.transition })
            }
          >
            {action.libelle}
          </button>
        ))}
        {!gereeAilleurs &&
          (editableIci(phase.sources) ? (
            <button type="button" className="bouton--discret" onClick={() => setEdition(true)}>
              Éditer
            </button>
          ) : (
            <span className="carte__etat" role="note">
              Composition avancée : éditable depuis l'écran de composition du déroulé.
            </span>
          ))}
        {!gereeAilleurs &&
          (confirmationSuppression ? (
            <>
              <button
                type="button"
                className="bouton--danger"
                disabled={supprimer.isPending}
                onClick={() => supprimer.mutate(phase.id)}
              >
                Confirmer la suppression
              </button>
              <button
                type="button"
                className="bouton--discret"
                onClick={() => setConfirmationSuppression(false)}
              >
                Annuler
              </button>
            </>
          ) : (
            <button
              type="button"
              className="bouton--danger"
              onClick={() => setConfirmationSuppression(true)}
            >
              Supprimer
            </button>
          ))}
      </div>
      <MessageErreur erreur={reordonner.error} />
      <MessageErreur erreur={changerStatut.error} />
      <MessageErreur erreur={supprimer.error} />
    </li>
  )
}

// Formulaire partagé création / édition : sans `phase` il ajoute (en fin de séquence), avec il édite.
function FormulairePhase({
  tournoiId,
  phases,
  phase,
  onTermine,
}: {
  tournoiId: number
  phases: Phase[]
  phase?: Phase
  onTermine?: () => void
}) {
  const enEdition = phase !== undefined
  const [type, setType] = useState<TypePhase>(phase?.type ?? 'elimination_directe')
  const [effectif, setEffectif] = useState(phase?.effectif != null ? String(phase.effectif) : '')
  const premiereSource = phase?.sources?.[0] ?? null
  const [avecSource, setAvecSource] = useState(premiereSource != null)
  const [ordreSource, setOrdreSource] = useState(
    premiereSource != null ? String(premiereSource.ordre_source) : '',
  )
  const [rangDebut, setRangDebut] = useState(
    premiereSource != null ? String(premiereSource.rang_debut) : '1',
  )
  // Vide = fin ouverte (« et suivants ») : c'est ce qui permet à un format composé pour 120
  // archers d'en accueillir 82 sans être réécrit (E05US010).
  const [rangFin, setRangFin] = useState(
    premiereSource?.rang_fin != null ? String(premiereSource.rang_fin) : '',
  )

  const ajouter = useAjouterPhase(tournoiId)
  const modifier = useModifierPhase(tournoiId)
  const mutation = enEdition ? modifier : ajouter

  // Sources possibles : les phases **antérieures** (ordre strictement inférieur). En ajout, la
  // future phase prend le dernier rang, donc toutes les phases existantes sont éligibles.
  const ordreCible = enEdition ? phase.ordre : phases.length + 1
  const sourcesPossibles = phases.filter((p) => p.ordre < ordreCible)

  // En édition, seuls les types composables sont proposés ; on garde le type courant même s'il n'y
  // figure pas (ex. qualification éditée par mégarde), pour ne pas le perdre au rendu du <select>.
  const typesProposes = TYPES_AJOUTABLES.includes(type)
    ? TYPES_AJOUTABLES
    : [type, ...TYPES_AJOUTABLES]

  const construireSources = (): SourcePhase[] | 'invalide' => {
    if (!avecSource) return []
    const os = Number(ordreSource)
    const rd = Number(rangDebut)
    // Rang de fin laissé vide = plage à fin ouverte (`null` côté serveur), pas une saisie fautive.
    const ouverte = rangFin.trim() === ''
    const rf = Number(rangFin)
    if (!ordreSource || !Number.isInteger(rd) || rd < 1) return 'invalide'
    if (!ouverte && (!Number.isInteger(rf) || rf < rd)) return 'invalide'
    return [
      {
        ordre_source: os,
        nature: 'rangs',
        rang_debut: rd,
        rang_fin: ouverte ? null : rf,
        tour: null,
        issue: null,
      },
    ]
  }

  const sources = construireSources()
  const effectifAnalyse = effectif.trim() === '' ? null : Number(effectif)
  const effectifInvalide =
    effectifAnalyse !== null && (!Number.isInteger(effectifAnalyse) || effectifAnalyse < 1)
  const soumissionPossible = sources !== 'invalide' && !effectifInvalide

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (sources === 'invalide' || effectifInvalide) return
    const config: ConfigPhase = { type, sources, effectif: effectifAnalyse }
    if (enEdition) {
      modifier.mutate({ phaseId: phase.id, config }, { onSuccess: onTermine })
    } else {
      ajouter.mutate(config, {
        onSuccess: () => {
          setEffectif('')
          setAvecSource(false)
          setOrdreSource('')
          setRangDebut('1')
          setRangFin('')
        },
      })
    }
  }

  return (
    <div>
      {enEdition && <h4 className="carte__soustitre">Modifier la phase {phase.ordre}</h4>}
      <form className="formulaire formulaire--colonne" onSubmit={soumettre}>
        <select
          className="formulaire__champ"
          value={type}
          onChange={(e) => setType(e.target.value as TypePhase)}
          aria-label="Type de la phase"
        >
          {typesProposes.map((valeur) => (
            <option key={valeur} value={valeur}>
              {LIBELLE_TYPE[valeur]}
            </option>
          ))}
        </select>
        <label className="formulaire__libelle">
          Effectif attendu (facultatif)
          <input
            className="formulaire__champ"
            inputMode="numeric"
            value={effectif}
            onChange={(e) => setEffectif(e.target.value)}
            placeholder="ex. 16 (participants classés)"
            aria-label="Effectif attendu de la phase"
          />
          {effectifInvalide && (
            <span className="carte__etat carte__etat--erreur" role="alert">
              Effectif attendu : un entier ≥ 1, ou vide (non déclaré).
            </span>
          )}
        </label>
        <label className="formulaire__tranche">
          <input
            type="checkbox"
            checked={avecSource}
            onChange={(e) => setAvecSource(e.target.checked)}
            disabled={sourcesPossibles.length === 0}
          />
          Alimentée par une phase antérieure
        </label>
        {avecSource && (
          <fieldset className="formulaire__champ formulaire__tranches">
            <legend>Source de peuplement</legend>
            <select
              className="formulaire__champ"
              value={ordreSource}
              onChange={(e) => setOrdreSource(e.target.value)}
              aria-label="Phase source"
            >
              <option value="">Phase source…</option>
              {sourcesPossibles.map((p) => (
                <option key={p.id} value={String(p.ordre)}>
                  Phase {p.ordre} — {LIBELLE_TYPE[p.type]}
                </option>
              ))}
            </select>
            <input
              className="formulaire__champ"
              inputMode="numeric"
              value={rangDebut}
              onChange={(e) => setRangDebut(e.target.value)}
              placeholder="Rang de début (ex. 1)"
              aria-label="Rang de début"
            />
            <input
              className="formulaire__champ"
              inputMode="numeric"
              value={rangFin}
              onChange={(e) => setRangFin(e.target.value)}
              placeholder="Rang de fin (vide = et suivants)"
              aria-label="Rang de fin"
            />
            {sources === 'invalide' && (
              <span className="carte__etat carte__etat--erreur" role="alert">
                Source incomplète : choisissez une phase et un rang de début ≥ 1. Le rang de fin est
                facultatif — le laisser vide prélève « et suivants », jusqu'au dernier classé.
              </span>
            )}
          </fieldset>
        )}
        <div className="formulaire__actions">
          <button type="submit" disabled={mutation.isPending || !soumissionPossible}>
            {enEdition ? 'Enregistrer' : 'Ajouter la phase'}
          </button>
          {enEdition && (
            <button type="button" className="bouton--discret" onClick={onTermine}>
              Annuler
            </button>
          )}
        </div>
      </form>
      <MessageErreur erreur={mutation.error} />
    </div>
  )
}
