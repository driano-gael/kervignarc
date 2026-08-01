// Écran « Composer un déroulé » (E01US024, ADR-0063) — axe **atelier**, sans tournoi.
//
// Il livre les cinq promesses du CA : composer une séquence complète en **brouillon**, la **voir**
// (schéma à braquets), savoir si elle **tient debout** (anomalies rattachées aux blocs), la
// **faire tourner** (simulation sur N archers fictifs), et **changer l'effectif** sans la retoucher.
//
// **Le brouillon est local, le diagnostic est serveur.** On édite une copie locale de la séquence,
// puis on enregistre : le schéma se recalcule alors depuis le serveur. Recalculer côté client
// obligerait à réimplémenter la *Règle R* en TypeScript — la duplication d'invariant que le
// registre de dette proscrit (cf. `domain/deroule.py`). Le prix est un aller-retour par
// modification ; le CA le rend indolore, puisqu'un brouillon s'enregistre à tout moment, même
// incohérent.
//
// Le modèle d'éditeur est `features/phases/Phases.tsx` (E05US001). Trois différences, toutes
// voulues : pas de **statut** (un modèle n'en a pas) ; la **qualification est éditable ici**
// (barème + grain), alors qu'un tournoi la règle depuis « Barème & validation » ; les **ordres sont
// dérivés de la position** dans la liste, jamais saisis — ce qui supprime par construction toute la
// classe d'erreurs « ordres non contigus ».

import { useMemo, useState } from 'react'

import { MessageErreur } from '../../shared/ui/MessageErreur'
import {
  AIDE_TYPE,
  LIBELLE_TYPE,
  TOUS_LES_TYPES,
  TYPES_SANS_CLASSEMENT,
  type TypePhase,
} from '../../shared/phases/catalogue'
import type { Etape, FormatTournoi, Source } from '../patrimoine/api'
import { useCreerFormat, useFormats, useModifierFormat } from '../patrimoine/hooks'
import { deplacer } from '../phases/ordre'
import type { Anomalie, Bloc, Diagnostic, PhaseSimulee, SimulationFormat } from './api'
import { useDiagnostic, useSimulerFormat } from './hooks'
import { disposer, type Arete, type Noeud } from './schema'

const EFFECTIF_PAR_DEFAUT = 120

export function Deroule() {
  const formats = useFormats()
  const [choix, setChoix] = useState<number | null>(null)
  const [effectifSaisi, setEffectifSaisi] = useState(String(EFFECTIF_PAR_DEFAUT))

  const effectif = analyserEffectif(effectifSaisi)
  // Le format courant est **dérivé**, jamais recopié dans un état : à défaut de choix explicite,
  // le premier de la bibliothèque ouvre l'écran (arriver sur une page vide alors que le club a des
  // formats donnerait à croire qu'il n'y en a aucun). Le faire en `useEffect` + `setState`
  // déclencherait un rendu en cascade — ce que `react-hooks/set-state-in-effect` refuse, à raison.
  const choisi = formats.data?.find((format) => format.id === choix) ?? formats.data?.[0] ?? null

  return (
    <section className="deroule">
      <header className="deroule__entete">
        <div className="formulaire__champ">
          <label className="formulaire__libelle" htmlFor="deroule-format">
            Format à composer
          </label>
          <select
            id="deroule-format"
            value={choisi?.id ?? ''}
            onChange={(evenement) => setChoix(Number(evenement.target.value))}
          >
            {(formats.data ?? []).map((format) => (
              <option key={format.id} value={format.id}>
                {format.nom}
                {format.origine === 'ffta' ? ' (FFTA)' : ''}
              </option>
            ))}
          </select>
        </div>
        <NouveauFormat surCreation={setChoix} />
        <div className="formulaire__champ">
          <label className="formulaire__libelle" htmlFor="deroule-effectif">
            Simuler avec N archers
          </label>
          <input
            id="deroule-effectif"
            inputMode="numeric"
            value={effectifSaisi}
            onChange={(evenement) => setEffectifSaisi(evenement.target.value)}
            aria-label="Effectif simulé"
          />
          <p className="carte__aide">
            Sans effectif, le déroulé reste abstrait : les braquets ne se calculent qu'à partir d'un
            nombre d'archers.
          </p>
        </div>
      </header>

      {choisi === null ? (
        <p className="carte__etat" role="note">
          Aucun format dans la bibliothèque du club : créez-en un pour composer son déroulé.
        </p>
      ) : (
        // `key` : changer de format **remonte** le composant, donc réinitialise son brouillon
        // depuis les props. C'est le remplaçant recommandé d'un `useEffect` de resynchronisation,
        // et il a un mérite propre — le brouillon d'un format ne peut pas fuiter sur un autre.
        <CompositionDuFormat key={choisi.id} format={choisi} effectif={effectif} />
      )}
    </section>
  )
}

function CompositionDuFormat({
  format,
  effectif,
}: {
  format: FormatTournoi
  effectif: number | null
}) {
  const [nom, setNom] = useState(format.nom)
  const [etapes, setEtapes] = useState<Etape[]>(format.etapes)
  const [modifie, setModifie] = useState(false)

  const diagnostic = useDiagnostic(format.id, effectif)
  const enregistrer = useModifierFormat()
  const simulation = useSimulerFormat(format.id)

  const majEtapes = (suivantes: Etape[]) => {
    // Les ordres sont **dérivés de la position**, jamais saisis : renuméroter ici est ce qui rend
    // « ordres non contigus » impossible depuis cet écran.
    setEtapes(suivantes.map((etape, index) => ({ ...etape, ordre: index + 1 })))
    setModifie(true)
  }

  return (
    <div className="deroule__colonnes">
      <div className="deroule__editeur">
        <EditeurSequence
          nom={nom}
          surNom={(valeur) => {
            setNom(valeur)
            setModifie(true)
          }}
          etapes={etapes}
          surEtapes={majEtapes}
        />
        <div className="formulaire__actions">
          <button
            type="button"
            disabled={!modifie || enregistrer.isPending}
            onClick={() =>
              enregistrer.mutate(
                { id: format.id, entree: { nom, etapes } },
                { onSuccess: () => setModifie(false) },
              )
            }
          >
            Enregistrer le brouillon
          </button>
          {modifie && (
            <span className="carte__etat" role="status">
              Modifications non enregistrées — le schéma montre encore la version enregistrée.
            </span>
          )}
        </div>
        <MessageErreur erreur={enregistrer.error} />
      </div>

      <div className="deroule__visuel">
        {diagnostic.data !== undefined && (
          <>
            <Verdict diagnostic={diagnostic.data} />
            <SchemaBraquets diagnostic={diagnostic.data} />
            <ListeAnomalies anomalies={diagnostic.data.anomalies} />
          </>
        )}
        <PanneauSimulation
          effectif={effectif}
          applicable={diagnostic.data?.applicable ?? false}
          simulation={simulation}
        />
      </div>
    </div>
  )
}

// --- Verdict & anomalies -------------------------------------------------------------------------

function Verdict({ diagnostic }: { diagnostic: Diagnostic }) {
  const bloquantes = diagnostic.anomalies.filter((a) => a.gravite === 'bloquante').length
  if (diagnostic.applicable) {
    return (
      <p className="carte__etat carte__etat--ok" role="status">
        ● Ce déroulé tient debout : il peut être appliqué à un tournoi.
      </p>
    )
  }
  return (
    <p className="carte__etat carte__etat--alerte" role="status">
      ▲ Ce brouillon est enregistré, mais {bloquantes} point(s) l'empêchent de servir un vrai
      tournoi.
    </p>
  )
}

function ListeAnomalies({ anomalies }: { anomalies: Anomalie[] }) {
  if (anomalies.length === 0) return null
  return (
    <ul className="deroule__anomalies">
      {anomalies.map((anomalie, index) => (
        <li
          key={`${anomalie.code}-${anomalie.ordre}-${index}`}
          className={`deroule__anomalie deroule__anomalie--${anomalie.gravite}`}
        >
          {/* `DV-03` : jamais la couleur seule — une pastille et un mot portent le sens. */}
          <span aria-hidden="true">{anomalie.gravite === 'bloquante' ? '●' : '▲'}</span>{' '}
          <strong>
            {anomalie.gravite === 'bloquante' ? 'Bloquant' : 'À vérifier'}
            {anomalie.ordre === null ? '' : ` — phase ${anomalie.ordre}`} :
          </strong>{' '}
          {anomalie.message}
        </li>
      ))}
    </ul>
  )
}

// --- Le schéma à braquets ------------------------------------------------------------------------

/**
 * Dessine le déroulé : un bloc par phase, une flèche par prélèvement.
 *
 * SVG **maison**, sans bibliothèque (règle 11) ; la géométrie vient de `schema.ts`, testée à part.
 * Les couleurs passent par les variables CSS (`var(--accent)`, `var(--warn)`…) pour que le thème
 * clair/sombre suive sans code conditionnel.
 */
function SchemaBraquets({ diagnostic }: { diagnostic: Diagnostic }) {
  const plan = useMemo(() => disposer(diagnostic.blocs), [diagnostic.blocs])
  if (diagnostic.blocs.length === 0) {
    return (
      <p className="carte__etat" role="note">
        Ce format ne décrit encore aucune phase : ajoutez-en une pour voir le déroulé se dessiner.
      </p>
    )
  }
  const parOrdre = new Map(diagnostic.blocs.map((bloc) => [bloc.ordre, bloc]))
  return (
    <div className="deroule__schema">
      <svg
        viewBox={`0 0 ${plan.largeur} ${plan.hauteur}`}
        width={plan.largeur}
        height={plan.hauteur}
        role="img"
        aria-label="Schéma du déroulé, une case par phase et une flèche par prélèvement"
      >
        <defs>
          <marker
            id="deroule-pointe"
            markerWidth="8"
            markerHeight="8"
            refX="7"
            refY="4"
            orient="auto"
          >
            <path d="M 0 0 L 8 4 L 0 8 z" fill="var(--accent)" />
          </marker>
        </defs>
        {plan.aretes.map((arete) => (
          <FlecheDuSchema key={arete.cle} arete={arete} />
        ))}
        {plan.noeuds.map((noeud) => {
          const bloc = parOrdre.get(noeud.ordre)
          return bloc === undefined ? null : (
            <BlocDuSchema key={noeud.ordre} noeud={noeud} bloc={bloc} />
          )
        })}
      </svg>
    </div>
  )
}

function FlecheDuSchema({ arete }: { arete: Arete }) {
  return (
    <g className="deroule__fleche">
      <path d={arete.trace} markerEnd="url(#deroule-pointe)" />
      <text x={arete.etiquette_x} y={arete.etiquette_y} textAnchor="middle">
        {arete.effectif === null ? '?' : arete.effectif}
      </text>
    </g>
  )
}

function BlocDuSchema({ noeud, bloc }: { noeud: Noeud; bloc: Bloc }) {
  const bloquant = bloc.anomalies.some((a) => a.gravite === 'bloquante')
  const alerte = bloc.anomalies.length > 0
  const modificateur = bloquant
    ? ' deroule__bloc--bloquant'
    : alerte
      ? ' deroule__bloc--alerte'
      : ''
  return (
    <g className={`deroule__bloc${modificateur}`} transform={`translate(${noeud.x} ${noeud.y})`}>
      <rect width={noeud.largeur} height={noeud.hauteur} rx="10" />
      <text className="deroule__bloc-titre" x="12" y="24">
        {bloc.ordre}. {LIBELLE_TYPE[bloc.type]}
      </text>
      {/* Question 1 du CA : qui est là — combien, et quelle tranche de rangs. */}
      <text className="deroule__bloc-ligne" x="12" y="46">
        {bloc.effectif === null ? 'effectif inconnu' : `${bloc.effectif} archers`}
        {bloc.tranche === null ? '' : ` · rangs ${bloc.tranche[0]}–${bloc.tranche[1]}`}
      </text>
      {/* Question 2 : ce qu'on leur demande. */}
      <text className="deroule__bloc-ligne" x="12" y="64">
        {bloc.nb_volees === null
          ? LIBELLE_TYPE[bloc.type] === LIBELLE_TYPE.qualification
            ? 'barème à définir'
            : 'duels'
          : `${bloc.nb_volees} volées de ${bloc.nb_fleches_par_volee}`}
      </text>
      {/* Question 4 : combien de tours — et la Règle R, tour par tour. */}
      {bloc.tours.map((tour, index) => (
        <text className="deroule__bloc-braquet" key={tour.tour} x="12" y={88 + index * 18}>
          T{tour.tour} · {tour.duels} duel(s) → perdants rangs {tour.plage_perdants[0]}–
          {tour.plage_perdants[1]}
        </text>
      ))}
      {/* Question 3 : où ils vont après — ce qui reste s'arrête ici. */}
      <text className="deroule__bloc-ligne" x="12" y={noeud.hauteur - 14}>
        {bloc.sans_suite === null
          ? 'suite inconnue'
          : bloc.sans_suite === 0
            ? 'tous repartent en phase suivante'
            : `${bloc.sans_suite} au classement final`}
      </text>
    </g>
  )
}

// --- La simulation -------------------------------------------------------------------------------

function PanneauSimulation({
  effectif,
  applicable,
  simulation,
}: {
  effectif: number | null
  applicable: boolean
  simulation: ReturnType<typeof useSimulerFormat>
}) {
  const resultat: SimulationFormat | undefined = simulation.data
  return (
    <div className="carte carte--large">
      <h3 className="carte__titre">Faire tourner le déroulé</h3>
      <p className="carte__aide">
        Joue le format sur des archers fictifs et rend ce qu'il produit : la charge réelle en duels,
        les tours par phase, et le classement 1→N. Rien n'est enregistré.
      </p>
      <button
        type="button"
        disabled={effectif === null || !applicable || simulation.isPending}
        onClick={() => effectif !== null && simulation.mutate(effectif)}
      >
        {simulation.isPending ? 'Simulation en cours…' : `Simuler à ${effectif ?? '—'} archers`}
      </button>
      {!applicable && (
        <p className="carte__etat" role="note">
          On ne simule pas un déroulé qu'aucun tournoi ne pourrait recevoir : corrigez d'abord les
          points bloquants.
        </p>
      )}
      <MessageErreur erreur={simulation.error} />
      {resultat !== undefined && <ResultatSimulation resultat={resultat} />}
    </div>
  )
}

function ResultatSimulation({ resultat }: { resultat: SimulationFormat }) {
  return (
    <div className="deroule__resultat">
      <p className="carte__etat carte__etat--ok" role="status">
        ● {resultat.effectif} archers, {resultat.volees_total} volées tirées,{' '}
        <strong>{resultat.duels_total} duels</strong> au total.
      </p>
      <table className="deroule__table">
        <caption>Ce que chaque phase a coûté</caption>
        <thead>
          <tr>
            <th scope="col">Phase</th>
            <th scope="col">Archers</th>
            <th scope="col">Tours</th>
            <th scope="col">Duels</th>
          </tr>
        </thead>
        <tbody>
          {resultat.phases.map((phase) => (
            <LignePhaseSimulee key={phase.ordre} phase={phase} />
          ))}
        </tbody>
      </table>
      <details>
        <summary>Classement produit ({resultat.classement.length} archers)</summary>
        <ol className="deroule__classement">
          {resultat.classement.slice(0, 32).map((ligne) => (
            <li key={`${ligne.rang}-${ligne.nom}-${ligne.prenom}`}>
              {ligne.rang}. {ligne.prenom} {ligne.nom} — {ligne.total}
            </li>
          ))}
        </ol>
      </details>
    </div>
  )
}

function LignePhaseSimulee({ phase }: { phase: PhaseSimulee }) {
  return (
    <tr className={phase.ecart ? 'deroule__ligne--ecart' : undefined}>
      <th scope="row">
        {phase.ordre}. {LIBELLE_TYPE[phase.type]}
      </th>
      <td>
        {phase.effectif}
        {/* Honnêteté d'outil : le moteur d'exécution ne lit pas encore le prélèvement déclaré
            (DETTE-028). Plutôt que de servir un chiffre faux et muet à qui dimensionne ses
            scoreurs, on montre l'écart avec ce que le schéma annonçait. */}
        {phase.ecart && (
          <span className="deroule__ecart" role="note">
            {' '}
            ▲ le schéma en annonçait {phase.effectif_projete} — le moteur ne sait pas encore
            appliquer ce prélèvement en duels
          </span>
        )}
      </td>
      <td>{phase.tours === 0 ? '—' : phase.tours}</td>
      <td>{phase.duels === 0 ? '—' : phase.duels}</td>
    </tr>
  )
}

// --- L'éditeur de séquence -----------------------------------------------------------------------

function EditeurSequence({
  nom,
  surNom,
  etapes,
  surEtapes,
}: {
  nom: string
  surNom: (valeur: string) => void
  etapes: Etape[]
  surEtapes: (etapes: Etape[]) => void
}) {
  const [edition, setEdition] = useState<number | null>(null)
  return (
    <div className="carte carte--large">
      <h3 className="carte__titre">Composer la séquence</h3>
      <div className="formulaire__champ">
        <label className="formulaire__libelle" htmlFor="deroule-nom">
          Nom du format
        </label>
        <input id="deroule-nom" value={nom} onChange={(e) => surNom(e.target.value)} />
      </div>
      <ol className="liste-phases">
        {etapes.map((etape, index) => (
          <li className="phase" key={`${etape.ordre}-${etape.type}-${index}`}>
            {edition === index ? (
              <FormulaireEtape
                etape={etape}
                etapesAmont={etapes.slice(0, index)}
                surValider={(modifiee) => {
                  surEtapes(etapes.map((e, i) => (i === index ? modifiee : e)))
                  setEdition(null)
                }}
                surAnnuler={() => setEdition(null)}
              />
            ) : (
              <div className="phase__ligne">
                <span className="phase__ordre">{index + 1}</span>
                <span className="phase__type">{LIBELLE_TYPE[etape.type]}</span>
                <span className="phase__details">{decrireEtapeCourte(etape)}</span>
                <span className="phase__actions">
                  <button
                    type="button"
                    className="bouton--discret"
                    disabled={index === 0}
                    onClick={() => surEtapes(deplacer(etapes, index, index - 1))}
                    aria-label={`Monter la phase ${index + 1}`}
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    className="bouton--discret"
                    disabled={index === etapes.length - 1}
                    onClick={() => surEtapes(deplacer(etapes, index, index + 1))}
                    aria-label={`Descendre la phase ${index + 1}`}
                  >
                    ↓
                  </button>
                  <button
                    type="button"
                    className="bouton--discret"
                    onClick={() => setEdition(index)}
                  >
                    Éditer
                  </button>
                  <button
                    type="button"
                    className="bouton--danger"
                    onClick={() => surEtapes(etapes.filter((_, i) => i !== index))}
                  >
                    Retirer
                  </button>
                </span>
              </div>
            )}
          </li>
        ))}
      </ol>
      <FormulaireEtape
        etapesAmont={etapes}
        surValider={(nouvelle) => surEtapes([...etapes, nouvelle])}
      />
    </div>
  )
}

/** Décrit une étape en une ligne, pour la liste de composition. */
function decrireEtapeCourte(etape: Etape): string {
  const morceaux: string[] = []
  if (etape.bareme !== null) {
    morceaux.push(`${etape.bareme.nb_volees}×${etape.bareme.nb_fleches_par_volee}`)
  }
  if (etape.effectif !== null) morceaux.push(`${etape.effectif} archers`)
  if (etape.sources.length === 0) morceaux.push('tous les inscrits')
  else morceaux.push(etape.sources.map(decrireSource).join(' + '))
  return morceaux.join(' · ')
}

function decrireSource(source: Source): string {
  if (source.nature === 'reste') return `le reste de la phase ${source.ordre_source}`
  if (source.nature === 'issue_de_tour') {
    return `${source.issue ?? '?'} du tour ${source.tour ?? '?'} (phase ${source.ordre_source})`
  }
  const fin = source.rang_fin === null ? 'et suivants' : `à ${source.rang_fin}`
  return `rangs ${source.rang_debut} ${fin} (phase ${source.ordre_source})`
}

function FormulaireEtape({
  etape,
  etapesAmont,
  surValider,
  surAnnuler,
}: {
  etape?: Etape
  etapesAmont: Etape[]
  surValider: (etape: Etape) => void
  surAnnuler?: () => void
}) {
  const [type, setType] = useState<TypePhase>(etape?.type ?? 'qualification')
  const [nbVolees, setNbVolees] = useState(String(etape?.bareme?.nb_volees ?? 20))
  const [nbFleches, setNbFleches] = useState(String(etape?.bareme?.nb_fleches_par_volee ?? 3))
  const [effectif, setEffectif] = useState(
    etape?.effectif === null ? '' : String(etape?.effectif ?? ''),
  )
  const [sources, setSources] = useState<Source[]>(etape?.sources ?? [])

  const construire = (): Etape => ({
    ordre: etape?.ordre ?? etapesAmont.length + 1,
    type,
    // La qualification, et elle seule, porte barème et grain — c'est ce que le domaine exige, et
    // les proposer ailleurs offrirait un réglage que le serveur refuse (422).
    bareme:
      type === 'qualification'
        ? { nb_volees: Number(nbVolees), nb_fleches_par_volee: Number(nbFleches) }
        : null,
    validation: type === 'qualification' ? { type: 'fin_de_serie', n_volees: null } : null,
    sources,
    effectif: effectif.trim() === '' ? null : Number(effectif),
  })

  return (
    <form
      className="formulaire formulaire--colonne"
      onSubmit={(evenement) => {
        evenement.preventDefault()
        surValider(construire())
        if (surAnnuler === undefined) {
          setSources([])
          setEffectif('')
        }
      }}
    >
      <div className="formulaire__champ">
        <label className="formulaire__libelle">Type de phase</label>
        <select value={type} onChange={(e) => setType(e.target.value as TypePhase)}>
          {TOUS_LES_TYPES.map((valeur) => (
            <option key={valeur} value={valeur}>
              {LIBELLE_TYPE[valeur]}
            </option>
          ))}
        </select>
        <p className="carte__aide">{AIDE_TYPE[type]}</p>
      </div>

      {type === 'qualification' && (
        <div className="formulaire__tranche">
          <label className="formulaire__libelle">
            Volées
            <input
              inputMode="numeric"
              value={nbVolees}
              onChange={(e) => setNbVolees(e.target.value)}
            />
          </label>
          <label className="formulaire__libelle">
            Flèches par volée
            <input
              inputMode="numeric"
              value={nbFleches}
              onChange={(e) => setNbFleches(e.target.value)}
            />
          </label>
        </div>
      )}

      <div className="formulaire__champ">
        <label className="formulaire__libelle">
          Effectif déclaré (vide = déduit des prélèvements)
          <input
            inputMode="numeric"
            value={effectif}
            onChange={(e) => setEffectif(e.target.value)}
          />
        </label>
      </div>

      <EditeurSources etapesAmont={etapesAmont} sources={sources} surSources={setSources} />

      <div className="formulaire__actions">
        <button type="submit">{etape === undefined ? 'Ajouter la phase' : 'Valider'}</button>
        {surAnnuler !== undefined && (
          <button type="button" className="bouton--discret" onClick={surAnnuler}>
            Annuler
          </button>
        )}
      </div>
    </form>
  )
}

/**
 * Compose les **prélèvements** d'une phase — plusieurs, de natures mêlées (E05US010).
 *
 * C'est la seconde moitié de DETTE-015 : l'écran « Phases » n'édite qu'un prélèvement par rangs et
 * affiche les compositions riches en lecture seule, en renvoyant explicitement « éditable depuis
 * l'écran de composition du déroulé ». C'est cet écran-là.
 */
function EditeurSources({
  etapesAmont,
  sources,
  surSources,
}: {
  etapesAmont: Etape[]
  sources: Source[]
  surSources: (sources: Source[]) => void
}) {
  const [nature, setNature] = useState<Source['nature']>('rangs')
  const [ordreSource, setOrdreSource] = useState('')
  const [rangDebut, setRangDebut] = useState('1')
  const [rangFin, setRangFin] = useState('')
  const [tour, setTour] = useState('1')
  const [issue, setIssue] = useState<'gagnants' | 'perdants'>('gagnants')

  // Une phase qui ne produit aucun classement ne se prélève que par « le reste » : le serveur le
  // refuse (`PhaseSansClassementPrelevee`), autant ne pas offrir le choix.
  const amontEligibles =
    nature === 'reste'
      ? etapesAmont
      : etapesAmont.filter((etape) => !TYPES_SANS_CLASSEMENT.includes(etape.type))

  const ajouter = () => {
    const ordre = Number(ordreSource)
    if (!Number.isInteger(ordre) || ordre < 1) return
    surSources([
      ...sources,
      {
        ordre_source: ordre,
        nature,
        rang_debut: nature === 'rangs' ? Number(rangDebut) : 1,
        rang_fin: nature === 'rangs' && rangFin.trim() !== '' ? Number(rangFin) : null,
        tour: nature === 'issue_de_tour' ? Number(tour) : null,
        issue: nature === 'issue_de_tour' ? issue : null,
      },
    ])
  }

  return (
    <fieldset className="deroule__sources">
      <legend>D'où viennent les archers</legend>
      {sources.length === 0 ? (
        <p className="carte__aide">Aucun prélèvement : cette phase accueille tous les inscrits.</p>
      ) : (
        <ul>
          {sources.map((source, index) => (
            <li key={`${source.ordre_source}-${source.nature}-${index}`}>
              {decrireSource(source)}{' '}
              <button
                type="button"
                className="bouton--discret"
                onClick={() => surSources(sources.filter((_, i) => i !== index))}
                aria-label={`Retirer le prélèvement ${index + 1}`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
      {etapesAmont.length === 0 ? (
        <p className="carte__aide">
          Première phase de la séquence : elle ne peut puiser dans aucune autre.
        </p>
      ) : (
        <div className="formulaire__tranche">
          <select
            value={nature}
            onChange={(e) => setNature(e.target.value as Source['nature'])}
            aria-label="Nature du prélèvement"
          >
            <option value="rangs">Rangs</option>
            <option value="issue_de_tour">Issue d'un tour</option>
            <option value="reste">Le reste</option>
          </select>
          <select
            value={ordreSource}
            onChange={(e) => setOrdreSource(e.target.value)}
            aria-label="Phase d'origine"
          >
            <option value="">Phase…</option>
            {amontEligibles.map((etape) => (
              <option key={etape.ordre} value={etape.ordre}>
                {etape.ordre}. {LIBELLE_TYPE[etape.type]}
              </option>
            ))}
          </select>
          {nature === 'rangs' && (
            <>
              <input
                inputMode="numeric"
                value={rangDebut}
                onChange={(e) => setRangDebut(e.target.value)}
                aria-label="Rang de début"
              />
              <input
                inputMode="numeric"
                value={rangFin}
                onChange={(e) => setRangFin(e.target.value)}
                placeholder="fin (vide = et suivants)"
                aria-label="Rang de fin"
              />
            </>
          )}
          {nature === 'issue_de_tour' && (
            <>
              <input
                inputMode="numeric"
                value={tour}
                onChange={(e) => setTour(e.target.value)}
                aria-label="Numéro de tour"
              />
              <select
                value={issue}
                onChange={(e) => setIssue(e.target.value as 'gagnants' | 'perdants')}
                aria-label="Côté prélevé"
              >
                <option value="gagnants">Gagnants</option>
                <option value="perdants">Perdants</option>
              </select>
            </>
          )}
          <button type="button" className="bouton--discret" onClick={ajouter}>
            Ajouter ce prélèvement
          </button>
        </div>
      )}
    </fieldset>
  )
}

// --- Création d'un format vide -------------------------------------------------------------------

function NouveauFormat({ surCreation }: { surCreation: (id: number) => void }) {
  const [nom, setNom] = useState('')
  const creer = useCreerFormat()
  return (
    <form
      className="formulaire"
      onSubmit={(evenement) => {
        evenement.preventDefault()
        if (nom.trim() === '') return
        // Un format **vide** est un brouillon parfaitement licite depuis E01US024 : c'est même
        // l'état normal de celui qu'on vient de nommer.
        creer.mutate(
          { nom, etapes: [] },
          {
            onSuccess: (cree: FormatTournoi) => {
              surCreation(cree.id)
              setNom('')
            },
          },
        )
      }}
    >
      <label className="formulaire__libelle">
        Nouveau format
        <input value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom du déroulé" />
      </label>
      <button type="submit" className="bouton--discret" disabled={creer.isPending}>
        Créer
      </button>
      <MessageErreur erreur={creer.error} />
    </form>
  )
}

function analyserEffectif(saisi: string): number | null {
  const valeur = Number(saisi)
  if (saisi.trim() === '' || !Number.isInteger(valeur) || valeur < 1) return null
  return valeur
}
