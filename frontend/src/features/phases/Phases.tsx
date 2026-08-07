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
import type { ConfigPhase, EtapeDeroule, SourcePhase, TypePhase } from './api'
import {
  useAjouterPhase,
  useModifierPhase,
  usePhases,
  useReordonnerPhases,
  useSupprimerPhase,
} from './hooks'
import {
  AIDE_TYPE,
  LIBELLE_TYPE,
  TYPES_EN_TABLEAU,
  TYPES_SANS_CLASSEMENT,
} from '../../shared/phases/catalogue'
import { ChoixProfondeur } from '../../shared/phases/ChoixProfondeur'
import {
  decrireProfondeur,
  depuisProfondeur,
  estValide,
  versProfondeur,
  PROFONDEUR_AU_PRESET,
} from '../../shared/phases/profondeur'
import { ordreApresDeplacement, type Direction } from './ordre'
import { decrireSources, editableIci } from './source'

// Types composables ici (la qualification se règle via le barème). E05US015 peuple le catalogue :
// chaque entrée a son moteur côté domaine, conformément à ADR-0045 §2.
const TYPES_AJOUTABLES: TypePhase[] = [
  'elimination_directe',
  'placement',
  'echauffement',
  'barrage',
  'poules',
  'big_shoot_off',
  'suisse',
  'colline',
]

export function Phases({ tournoiId }: { tournoiId: number }) {
  const phases = usePhases(tournoiId)
  const liste = phases.data ?? []

  return (
    <section>
      <h3 className="carte__soustitre">Phases (déroulé du tournoi)</h3>
      <p className="carte__etat">
        Composez la suite des phases après la qualification (élimination directe, placement). La
        qualification se règle dans « Barème &amp; validation ». Ce déroulé est défini{' '}
        <strong>une fois</strong> : chaque départ le rejoue. Pour démarrer, mettre en pause ou
        terminer une phase sur un créneau donné, c'est « Suivi du déroulé ».
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

function LignePhase({
  tournoiId,
  phase,
  phases,
  premier,
  dernier,
}: {
  tournoiId: number
  phase: EtapeDeroule
  phases: EtapeDeroule[]
  premier: boolean
  dernier: boolean
}) {
  const [edition, setEdition] = useState(false)
  const [confirmationSuppression, setConfirmationSuppression] = useState(false)
  const reordonner = useReordonnerPhases(tournoiId)
  const supprimer = useSupprimerPhase(tournoiId)

  const deplacer = (direction: Direction) => {
    const ordre = ordreApresDeplacement(phases, phase.id, direction)
    if (ordre !== null) reordonner.mutate(ordre)
  }

  // La qualification se gère sur l'écran « Barème & validation » : on n'offre pas ici de l'éditer ni
  // de la supprimer (ce serait perdre son barème par surprise). Elle reste réordonnable.
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
        <span className="phase__details">
          {decrireSources(phase.sources)}
          {phase.effectif !== null && ` · ${phase.effectif} participants`}
          {/* Parité avec l'écran de composition, qui l'affiche déjà : sur un tournoi réel, le
              réglage le plus lourd de la journée ne doit pas n'être visible qu'en rouvrant le
              formulaire d'édition. Rien n'est dit d'une phase au preset — l'afficher partout ferait
              passer un défaut hérité pour une décision. */}
          {phase.profondeur !== null && ` · ${decrireProfondeur(phase.profondeur)}`}
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
        {gereeAilleurs && <ReglageBarrage tournoiId={tournoiId} phase={phase} />}
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
      <MessageErreur erreur={supprimer.error} />
    </li>
  )
}

// Formulaire partagé création / édition : sans `phase` il ajoute (en fin de séquence), avec il édite.
/** Exporté pour ses tests : c'est le seul des deux écrans de composition qui touche un tournoi
 * réel, et le `PUT` y est **total** — un champ non réémis est effacé côté serveur. */
export function FormulairePhase({
  tournoiId,
  phases,
  phase,
  onTermine,
}: {
  tournoiId: number
  phases: EtapeDeroule[]
  phase?: EtapeDeroule
  onTermine?: () => void
}) {
  const enEdition = phase !== undefined
  const [type, setType] = useState<TypePhase>(phase?.type ?? 'elimination_directe')
  const [effectif, setEffectif] = useState(phase?.effectif != null ? String(phase.effectif) : '')
  // **Source unique** du réglage de profondeur (E06US006), détenue ici et non dans le contrôle :
  // celui-ci est monté sous condition, donc une copie interne divergerait au premier aller-retour
  // de type. Le contrôle est partagé avec « Composer un déroulé » — le réglage y a le même sens.
  const [profondeur, setProfondeur] = useState(depuisProfondeur(phase?.profondeur ?? null))
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

  // Sources possibles : les phases **antérieures** (ordre strictement inférieur) **qui produisent
  // un classement**. En ajout, la future phase prend le dernier rang, donc toutes les phases
  // existantes sont éligibles.
  //
  // ⚠️ Le filtre sur les phases non classantes n'est pas cosmétique : ce formulaire ne sait
  // exprimer que le prélèvement « par rangs », et le serveur refuse (à juste titre) de prélever des
  // rangs dans un échauffement, qui n'en produit aucun. Sans le filtre, l'organisateur reçoit un
  // 422 dont la consigne — « reprendre le reste de ses participants » — n'est réalisable par aucun
  // écran : une impasse sans sortie. Le chemin réel reste ouvert (une phase peut n'avoir aucune
  // source, et « échauffement puis qualification » se compose ainsi sans encombre) ; la saisie du
  // prélèvement « le reste » arrive avec l'éditeur de composition (E01US024).
  const ordreCible = enEdition ? phase.ordre : phases.length + 1
  const sourcesPossibles = phases.filter(
    (p) => p.ordre < ordreCible && !TYPES_SANS_CLASSEMENT.includes(p.type),
  )

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
  const enTableau = TYPES_EN_TABLEAU.includes(type)
  const soumissionPossible =
    sources !== 'invalide' && !effectifInvalide && !(enTableau && !estValide(profondeur))

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!soumissionPossible) return
    // ⚠️ `barrage_jusqu_au` est **réémis tel quel** : le `PUT` est une édition **totale**, donc
    // l'omettre effacerait le seuil dès qu'on corrige un effectif. Il ne se **règle** pas ici (voir
    // `ReglageBarrage`, sur la qualification), il se **préserve**.
    const config: ConfigPhase = {
      type,
      sources,
      effectif: effectifAnalyse,
      barrage_jusqu_au: phase?.barrage_jusqu_au ?? null,
      // Même règle d'édition totale que le barrage — mais celle-ci se **règle** ici aussi : une
      // phase retypée hors tableau perd sa profondeur, puisque le serveur la refuserait (422).
      profondeur: enTableau ? (versProfondeur(profondeur) ?? null) : null,
    }
    if (enEdition) {
      modifier.mutate({ phaseId: phase.id, config }, { onSuccess: onTermine })
    } else {
      ajouter.mutate(config, {
        onSuccess: () => {
          setEffectif('')
          // La profondeur se remet au preset comme les autres champs de ce formulaire :
          // « classement intégral » est le réglage le plus coûteux de la journée, il ne doit pas
          // se reporter en silence d'une phase à la suivante. ⚠️ Le formulaire d'ajout de
          // « Composer un déroulé » ne réinitialise, lui, **aucun** champ (comportement antérieur
          // à cette US, type et effectif compris) : l'asymétrie est constatée, pas voulue.
          setProfondeur(PROFONDEUR_AU_PRESET)
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
          aria-describedby="aide-type-phase"
        >
          {typesProposes.map((valeur) => (
            <option key={valeur} value={valeur}>
              {LIBELLE_TYPE[valeur]}
            </option>
          ))}
        </select>
        {/* L'aide suit le type choisi : sans elle, « Colline » ou « Suisse » ne disent rien à un
            organisateur qui découvre le catalogue élargi par E05US015. */}
        <p className="carte__aide" id="aide-type-phase">
          {AIDE_TYPE[type]}
        </p>
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
        {enTableau && (
          <ChoixProfondeur
            etat={profondeur}
            surChangement={setProfondeur}
            presetIntegral={type === 'placement'}
          />
        )}
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

/** Réglage du **barrage** sur la phase de qualification (E06US003, ADR-0066).
 *
 * ⚠️ **Il vit ici et nulle part ailleurs, et c'est un correctif de revue.** Le champ avait d'abord
 * été ajouté à `FormulairePhase` — que la qualification **n'ouvre jamais** (`gereeAilleurs`) : le
 * seuil restait donc réglable par aucun écran, alors que `ServiceClassement` ne le lit que sur la
 * phase de qualification. Le trou avait été déplacé, pas fermé.
 *
 * Contrôle **réduit au seul seuil** : le `PUT` de phase est une édition totale, donc on réémet
 * `type`, `sources` et `effectif` tels que la phase les porte. Rouvrir le formulaire complet sur la
 * qualification risquerait au contraire d'écraser son barème par surprise — la raison même pour
 * laquelle elle est « gérée ailleurs ».
 */
function ReglageBarrage({ tournoiId, phase }: { tournoiId: number; phase: EtapeDeroule }) {
  const [valeur, setValeur] = useState(
    phase.barrage_jusqu_au != null ? String(phase.barrage_jusqu_au) : '',
  )
  const modifier = useModifierPhase(tournoiId)
  const analyse = valeur.trim() === '' ? null : Number(valeur)
  const invalide = analyse !== null && (!Number.isInteger(analyse) || analyse < 1)

  const enregistrer = () => {
    if (invalide) return
    modifier.mutate({
      phaseId: phase.id,
      config: {
        type: phase.type,
        sources: phase.sources,
        effectif: phase.effectif,
        barrage_jusqu_au: analyse,
        // Réémise pour la même raison que le reste : le `PUT` est **total**. Inoffensif aujourd'hui
        // (ce widget n'est rendu que sur la qualification, qui ne porte jamais de profondeur), mais
        // c'était le seul chemin d'appel non audité par l'US — relevé en revue, fermé à une ligne.
        profondeur: phase.profondeur,
      },
    })
  }

  return (
    <div className="phase__barrage">
      <label>
        Barrage jusqu&apos;au rang{' '}
        <input
          className="formulaire__champ"
          inputMode="numeric"
          value={valeur}
          onChange={(e) => setValeur(e.target.value)}
          placeholder="aucun"
        />
      </label>
      <button
        type="button"
        className="bouton--discret"
        onClick={enregistrer}
        disabled={invalide || modifier.isPending}
      >
        Enregistrer
      </button>
      <span className="carte__aide">
        Vide = les ex æquo partagent leur rang (défaut). Renseigné, l&apos;application signale les
        égalités jusqu&apos;à ce rang et propose un tir de barrage.
      </span>
      {invalide && (
        <span className="carte__etat carte__etat--erreur" role="alert">
          Un entier ≥ 1, ou vide (aucun barrage).
        </span>
      )}
      {modifier.isError && (
        <span className="carte__etat carte__etat--erreur" role="alert">
          {modifier.error.message}
        </span>
      )}
    </div>
  )
}
