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

import { useState } from 'react'

import { MessageErreur } from '../../shared/ui/MessageErreur'
import {
  AIDE_TYPE,
  LIBELLE_TYPE,
  TOUS_LES_TYPES,
  TYPES_SANS_CLASSEMENT,
  type TypePhase,
} from '../../shared/phases/catalogue'
import type { Etape, FormatTournoi, Source } from '../patrimoine/api'
import { useCreerFormat, useFormats } from '../patrimoine/hooks'
import {
  EFFECTIF_MAX,
  type Anomalie,
  type Diagnostic,
  type PhaseSimulee,
  type SimulationFormat,
} from './api'
import { useDiagnostic, useEnregistrerBrouillon, useSimulerFormat } from './hooks'
import {
  ajouterEtape,
  decrireEtape,
  decrireSource,
  deplacerEtape,
  lireEntier,
  remplacerEtape,
  retirerEtape,
} from './sequence'
import { SchemaBraquets } from '../../shared/schema-braquets/SchemaBraquets'

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
            nombre d'archers. Entre 1 et {EFFECTIF_MAX}.
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
  const enregistrer = useEnregistrerBrouillon()
  const simulation = useSimulerFormat(format.id)

  // Les ordres sont **dérivés de la position**, jamais saisis, et `sequence.ts` **remappe** les
  // prélèvements en conséquence — sans quoi monter une phase d'un cran ferait glisser en silence
  // les `ordre_source` de ses cadettes sur la voisine (cf. `renumeroter`).
  const majEtapes = (suivantes: Etape[]) => {
    setEtapes(suivantes)
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
              enregistrer.enregistrer(
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
        {/* `isFetching` et non `isPending` : après une invalidation, `data` porte encore la
            version d'avant pendant le vol de la requête, et `isPending` est faux — le schéma
            périmé s'afficherait sans que rien ne le dise. */}
        {diagnostic.isFetching && (
          <p className="carte__etat" role="status">
            Calcul du déroulé…
          </p>
        )}
        <MessageErreur erreur={diagnostic.error} />
        {diagnostic.data !== undefined && (
          <>
            <Verdict diagnostic={diagnostic.data} />
            <ReserveMoteur diagnostic={diagnostic.data} />
            {/* Surface **atelier** : taille fixe (on lit les chiffres et on fait défiler), habillage
                outil (`D-27` : jamais d'identité de tournoi ici — on compose un modèle, pas une
                édition), et **aucun** calque d'avancement (il n'y a pas de réalité à superposer). */}
            <SchemaBraquets
              blocs={diagnostic.data.blocs}
              messageVide="Ce format ne décrit encore aucune phase : ajoutez-en une pour voir le déroulé se dessiner."
            />
            <ListeAnomalies anomalies={diagnostic.data.anomalies} />
          </>
        )}
        <PanneauSimulation
          effectif={effectif}
          diagnostic={diagnostic.data}
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

/**
 * La réserve que la vue par défaut doit porter (`# DETTE-028`).
 *
 * Le schéma est un **engagement dessiné** : il annonce « 32 duellistes » là où le moteur
 * d'exécution en ensemencera 120, faute de consommateur de `Phase.sources` côté duels. Sans cette
 * note, l'organisateur qui compose, voit le verdict vert, enregistre et applique — sans jamais
 * cliquer « Simuler » — repart avec un tournoi qui ne se déroulera pas comme dessiné. C'est
 * exactement le point où cette US **aggrave** la dette, et l'afficher est ce qui transforme une
 * promesse en information.
 */
function ReserveMoteur({ diagnostic }: { diagnostic: Diagnostic }) {
  if (!diagnostic.blocs.some((bloc) => bloc.entrees.length > 0)) return null
  return (
    <p className="carte__etat carte__etat--alerte" role="note">
      ▲ Le moteur d'exécution ne lit pas encore les prélèvements : le jour J, chaque tableau est
      ensemencé avec <strong>tous</strong> les archers encore en lice. Lancez la simulation pour
      voir l'écart entre ce déroulé et ce qui se jouera réellement.
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

// --- La simulation -------------------------------------------------------------------------------

function PanneauSimulation({
  effectif,
  diagnostic,
  simulation,
}: {
  effectif: number | null
  diagnostic: Diagnostic | undefined
  simulation: ReturnType<typeof useSimulerFormat>
}) {
  const resultat: SimulationFormat | undefined = simulation.data
  // Le serveur reste l'autorité (400 `format_non_simulable`) ; ce garde évite seulement d'offrir un
  // bouton dont on sait qu'il sera refusé — même parti que `TYPES_SANS_CLASSEMENT`.
  const aUneQualification = diagnostic?.blocs.some((bloc) => bloc.type === 'qualification') ?? false
  const applicable = diagnostic?.applicable ?? false
  const effectifValide = effectif !== null && effectif >= 2 && effectif <= EFFECTIF_MAX
  const empeche =
    diagnostic === undefined
      ? 'Le déroulé est en cours de calcul.'
      : !applicable
        ? 'On ne simule pas un déroulé qu’aucun tournoi ne pourrait recevoir : corrigez d’abord les points bloquants.'
        : !aUneQualification
          ? 'Ce déroulé ne décrit aucune qualification : la simulation n’a alors aucun barème d’où tirer des scores. Le format reste applicable à un tournoi.'
          : !effectifValide
            ? `Indiquez un effectif entre 2 et ${EFFECTIF_MAX} archers pour lancer la simulation.`
            : null
  return (
    <div className="carte carte--large">
      <h3 className="carte__titre">Faire tourner le déroulé</h3>
      <p className="carte__aide">
        Joue le format sur des archers fictifs et rend ce qu'il produit : la charge réelle en duels,
        les tours par phase, et le classement 1→N. Rien n'est enregistré.
      </p>
      <button
        type="button"
        disabled={empeche !== null || simulation.isPending}
        onClick={() => effectif !== null && simulation.mutate(effectif)}
      >
        {simulation.isPending ? 'Simulation en cours…' : `Simuler à ${effectif ?? '—'} archers`}
      </button>
      {empeche !== null && (
        <p className="carte__etat" role="note">
          {empeche}
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
      {resultat.phases.some((phase) => phase.ecart) && (
        <p className="carte__etat carte__etat--alerte" role="note">
          ▲ Ce total est une <strong>borne haute</strong> : sur au moins une phase, le moteur n'a
          pas joué ce que le schéma annonçait (voir la colonne « Archers »).
        </p>
      )}
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
        <summary>
          Classement produit ({resultat.classement.length} archers
          {resultat.classement.length > 32 ? ', 32 premiers affichés' : ''})
        </summary>
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
        {phase.joue ? phase.effectif : '—'}
        {/* Honnêteté d'outil : le moteur d'exécution ne lit pas encore le prélèvement déclaré, et
            ne sait dérouler ni les poules, ni le suisse, ni la colline (DETTE-028). Plutôt que de
            servir un chiffre faux et muet à qui dimensionne ses scoreurs, on montre l'écart avec ce
            que le schéma annonçait — et on dit quand le moteur n'a rien joué du tout. */}
        {!phase.joue ? (
          <span className="deroule__ecart" role="note">
            {' '}
            ▲ le moteur ne sait pas encore dérouler ce type de phase — rien n'a été joué ici
          </span>
        ) : (
          phase.ecart && (
            <span className="deroule__ecart" role="note">
              {' '}
              ▲ le schéma annonçait {phase.effectif_projete} archers, {phase.tours_projetes ?? '—'}{' '}
              tours et {phase.duels_projetes ?? '—'} duels
            </span>
          )
        )}
      </td>
      <td>{phase.joue && phase.tours > 0 ? phase.tours : '—'}</td>
      <td>{phase.joue && phase.duels > 0 ? phase.duels : '—'}</td>
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
                  surEtapes(remplacerEtape(etapes, index, modifiee))
                  setEdition(null)
                }}
                surAnnuler={() => setEdition(null)}
              />
            ) : (
              <div className="phase__ligne">
                <span className="phase__ordre">{index + 1}</span>
                <span className="phase__type">{LIBELLE_TYPE[etape.type]}</span>
                <span className="phase__details">{decrireEtape(etape)}</span>
                <span className="phase__actions">
                  <button
                    type="button"
                    className="bouton--discret"
                    disabled={index === 0}
                    onClick={() => surEtapes(deplacerEtape(etapes, index, index - 1))}
                    aria-label={`Monter la phase ${index + 1}`}
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    className="bouton--discret"
                    disabled={index === etapes.length - 1}
                    onClick={() => surEtapes(deplacerEtape(etapes, index, index + 1))}
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
                    onClick={() => surEtapes(retirerEtape(etapes, index))}
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
        surValider={(nouvelle) => surEtapes(ajouterEtape(etapes, nouvelle))}
      />
    </div>
  )
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

  const volees = lireEntier(nbVolees)
  const fleches = lireEntier(nbFleches)
  const effectifLu = lireEntier(effectif)
  // Un barème n'est porté que si **les deux** valeurs sont lisibles. Sinon `null` : c'est un
  // **brouillon** de qualification, l'état que le CA rend explicitement licite. Un premier jet
  // envoyait `Number('') === 0`, donc `0 volées` — refusé en 422 par `BaremeQualification`, si bien
  // que « je remplirai le barème plus tard » était le seul brouillon naturel… et le seul impossible.
  const baremeSaisi =
    type === 'qualification' && typeof volees === 'number' && typeof fleches === 'number'
      ? { nb_volees: volees, nb_fleches_par_volee: fleches }
      : null
  const saisieInvalide = volees === undefined || fleches === undefined || effectifLu === undefined

  const construire = (): Etape => ({
    ordre: etape?.ordre ?? etapesAmont.length + 1,
    type,
    // La qualification, et elle seule, porte barème et grain — c'est ce que le domaine exige, et
    // les proposer ailleurs offrirait un réglage que le serveur refuse (422).
    bareme: baremeSaisi,
    validation:
      type === 'qualification' && baremeSaisi !== null
        ? { type: 'fin_de_serie', n_volees: null }
        : null,
    sources,
    effectif: effectifLu ?? null,
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
        <button type="submit" disabled={saisieInvalide}>
          {etape === undefined ? 'Ajouter la phase' : 'Valider'}
        </button>
        {saisieInvalide && (
          <span className="carte__etat carte__etat--alerte" role="status">
            Un nombre entier positif est attendu — laissez le champ vide pour ne rien déclarer.
          </span>
        )}
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

  // Changer de nature **réinitialise** la phase choisie : « le reste » autorise les phases sans
  // classement, les deux autres non. Sans cette remise à zéro, le `<select>` s'affichait vide mais
  // l'état gardait l'ancienne valeur, et « Ajouter » créait un prélèvement par rangs sur un
  // échauffement — refusé en 422 par le serveur, sans explication à l'écran.
  const changerNature = (valeur: Source['nature']) => {
    setNature(valeur)
    setOrdreSource('')
  }

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
            onChange={(e) => changerNature(e.target.value as Source['nature'])}
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
          <button
            type="button"
            className="bouton--discret"
            disabled={ordreSource === ''}
            onClick={ajouter}
          >
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

/**
 * L'effectif simulé, borné **comme le serveur** (`EFFECTIF_MAX`).
 *
 * ⚠️ La borne serveur a été ajoutée sur `GET …/diagnostic` sans être propagée ici dans un premier
 * jet : saisir `300` envoyait la requête, revenait en 400 « Requête invalide. » — et faisait
 * **disparaître tout le schéma**, verdict et anomalies compris, derrière un message qui ne disait
 * même pas quelle était la borne. Avant l'ajout de la borne, ce cas rendait un diagnostic valide :
 * c'était donc une régression d'écran introduite par le correctif lui-même.
 */
function analyserEffectif(saisi: string): number | null {
  const valeur = lireEntier(saisi)
  if (typeof valeur !== 'number' || valeur > EFFECTIF_MAX) return null
  return valeur
}
