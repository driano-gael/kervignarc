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
  MOTEUR_SAIT_JOUER,
  TOUS_LES_TYPES,
  TYPES_EN_TABLEAU,
  TYPES_SANS_CLASSEMENT,
  TYPES_SIGNALES_EN_ECART,
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
import { ChoixProfondeur } from '../../shared/phases/ChoixProfondeur'
import { ReglagePoules } from '../../shared/phases/ReglagePoules'
import { ReglageBigShootOff } from '../../shared/phases/ReglageBigShootOff'
import {
  depuisReglage as depuisReglageBso,
  estValide as bsoValide,
  versReglage as versReglageBso,
  BIG_SHOOT_OFF_PAR_DEFAUT,
} from '../../shared/phases/bigShootOff'
import { ReglageSuisse } from '../../shared/phases/ReglageSuisse'
import {
  depuisReglage as depuisReglageSuisse,
  estValide as suisseValide,
  versReglage as versReglageSuisse,
  SUISSE_PAR_DEFAUT,
} from '../../shared/phases/suisse'
import {
  depuisReglage,
  estValide as poulesValides,
  versReglage,
  POULES_PAR_DEFAUT,
} from '../../shared/phases/poules'
import {
  depuisProfondeur,
  estValide,
  versProfondeur,
  PROFONDEUR_AU_PRESET,
} from '../../shared/phases/profondeur'

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
  // Saisi en **texte** comme l'effectif simulé : un champ numérique vidé doit pouvoir rester vide
  // pendant qu'on le retape, ce qu'un `number | null` piloté ferait perdre à chaque frappe.
  const [minimumExige, setMinimumExige] = useState(
    format.effectif_minimum_exige === null ? '' : String(format.effectif_minimum_exige),
  )
  const [modifie, setModifie] = useState(false)

  // `lireEntier` rend `null` (vide = aucune exigence), un entier, ou `undefined` (illisible).
  // ⚠️ Le `Number()` nu qui était ici **effaçait** la règle du club : `Number('quarante')` vaut
  // `NaN`, que `JSON.stringify` sérialise en `null` — le serveur comprenait « aucune exigence » et
  // répondait 200. Le même piège était déjà résolu deux fonctions plus bas pour l'effectif simulé ;
  // il n'avait pas été réappliqué ici.
  const exigenceSaisie = lireEntier(minimumExige)

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
          minimumExige={minimumExige}
          surMinimumExige={(valeur) => {
            setMinimumExige(valeur)
            setModifie(true)
          }}
          effectifSimule={effectif}
        />
        <div className="formulaire__actions">
          <button
            type="button"
            disabled={!modifie || enregistrer.isPending || exigenceSaisie === undefined}
            onClick={() =>
              enregistrer.enregistrer(
                {
                  id: format.id,
                  entree: { nom, etapes, effectif_minimum_exige: exigenceSaisie ?? null },
                },
                { onSuccess: () => setModifie(false) },
              )
            }
          >
            Enregistrer le brouillon
          </button>
          {exigenceSaisie === undefined && (
            <span className="carte__etat carte__etat--alerte" role="status">
              ▲ Le minimum d’inscrits doit être un nombre entier d’au moins 1 — ou vide.
            </span>
          )}
          {modifie && exigenceSaisie !== undefined && (
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
            <EffectifMinimum diagnostic={diagnostic.data} />
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
 * Le plancher d'inscrits de ce format (E05US021) — annoncé **qu'un effectif soit simulé ou non**.
 *
 * Deux registres, et c'est délibéré. Tant que le compte est bon (ou qu'on ne simule rien), c'est une
 * **information** neutre : `carte__aide`, pas d'alerte — le format n'a rien de fautif, il a
 * simplement un plancher. Dès que l'effectif simulé passe dessous, ça devient un **avertissement**
 * ambre (`--danger`, `DV-03`), avec glyphe *et* mot : à cet effectif-là, le tournoi ne se lancera pas.
 *
 * Jamais bloquant : un format composé pour 120 archers reste parfaitement valide le jour où l'on en
 * simule 28 — c'est la simulation qui ne correspond pas, pas le format. Le blocage n'a lieu qu'au
 * démarrage d'un vrai tournoi, où les inscrits sont des faits et non une hypothèse.
 */
export function EffectifMinimum({ diagnostic }: { diagnostic: Diagnostic }) {
  const minimum = diagnostic.effectif_minimum
  // 1 = « aucune exigence » : tout déroulé accueille au moins un archer. L'afficher ferait passer
  // une trivialité pour une contrainte.
  if (minimum <= 1) return null

  const insuffisant = diagnostic.effectif !== null && diagnostic.effectif < minimum
  if (!insuffisant) {
    return (
      <p className="carte__aide">
        Ce déroulé demande au moins <strong>{minimum} inscrits</strong> pour pouvoir être lancé.
      </p>
    )
  }
  return (
    <p className="carte__etat carte__etat--alerte" role="status">
      ▲ <strong>À vérifier</strong> — à {diagnostic.effectif} archers, ce déroulé ne peut pas être
      lancé : il en demande au moins {minimum}.
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
// Les types que le moteur ne sait **pas encore** exécuter — désormais domiciliés au catalogue
// partagé (`shared/phases/catalogue.ts`), et écrits en **négatif** : cf. la note qui les porte
// là-bas, un oubli y coûte un avertissement de trop plutôt qu'un avertissement de moins.
const EN_ECART = new Set<TypePhase>(TYPES_SIGNALES_EN_ECART)

export function ReserveMoteur({ diagnostic }: { diagnostic: Diagnostic }) {
  // ⚠️ **Reformulée, pas supprimée** (E05US020, ADR-0068). Le moteur lit désormais les
  // prélèvements **par rangs** : « les rangs 1 à 32 » monte bien un tableau de 32. Restent inertes
  // « le reste » et « les gagnants/perdants du tour N », dont la sémantique n'est tranchée nulle
  // part (DETTE-033) — la réserve ne s'affiche donc que si l'un d'eux est réellement déclaré.
  // Continuer à l'afficher sur un prélèvement par rangs aurait fait douter d'un déroulé désormais
  // exact ; la retirer entièrement aurait laissé croire que tout est honoré.
  // ⚠️ Deux causes distinctes d'inexactitude, et l'ancienne condition (`entrees.length > 0`) les
  // couvrait toutes les deux **par accident**. Les séparer était nécessaire — sinon la réserve
  // restait affichée sur un déroulé désormais exact — mais ne garder que la première aurait fait
  // disparaître l'avertissement d'un déroulé « qualification → poules », que le moteur ne sait
  // toujours pas dérouler du tout (relevé en contre-revue).
  const prelevementInerte = diagnostic.blocs.some((bloc) =>
    bloc.entrees.some((flux) => flux.nature !== 'rangs'),
  )
  // Les types **réellement** en cause, et non une liste figée. Le bandeau nommait « suisse,
  // colline, Big Shoot Off » en dur alors que `TYPES_SIGNALES_EN_ECART` en compte cinq : composer
  // une phase `placement` ou `barrage` allumait donc un avertissement qui désignait trois formats
  // que l'organisateur n'avait pas utilisés (correctif de revue). Le CA fait précisément de la
  // justesse de ce signal son exigence.
  const typesEnEcart = [...new Set(diagnostic.blocs.map((bloc) => bloc.type))].filter((type) =>
    EN_ECART.has(type),
  )
  const typeNonDeroule = typesEnEcart.length > 0
  if (!prelevementInerte && !typeNonDeroule) return null
  return (
    <p className="carte__etat carte__etat--alerte" role="note">
      ▲ Ce déroulé contient quelque chose que le moteur ne sait <strong>pas encore</strong> exécuter
      {prelevementInerte && (
        <>
          {' '}
          — un prélèvement « le reste » ou « les gagnants/perdants d'un tour », dont la phase
          concernée prendra <strong>tous</strong> les archers encore en lice
        </>
      )}
      {typeNonDeroule && (
        <>
          {' '}
          — un type de phase qu&apos;il ne déroule pas (
          {typesEnEcart.map((type) => LIBELLE_TYPE[type]).join(', ')})
        </>
      )}
      . Les prélèvements <strong>par rangs</strong>, eux, sont respectés. Lancez la simulation pour
      voir l'écart.
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
        {/* Honnêteté d'outil : le moteur ne sait dérouler ni les poules, ni le suisse, ni la
            colline (DETTE-028), et n'honore pas les prélèvements « le reste » / « issue de tour »
            (ADR-0068 §3). Plutôt que de servir un chiffre faux et muet à qui dimensionne ses
            scoreurs, on montre l'écart avec ce que le schéma annonçait — et on dit quand le moteur
            n'a rien joué du tout. Les prélèvements **par rangs** sont désormais honorés (E05US020),
            donc l'écart s'y referme de lui-même. */}
        {/* ⚠️ **Deux phrases, parce qu'il y a deux causes** (correctif de revue E05US028). E05US023
            puis E05US028 ont rendu les poules et le Big Shoot Off **jouables par le moteur**, mais
            le *bot de simulation* ne sait toujours pas les jouer (`_TYPES_DEROULABLES` les exclut
            explicitement, côté serveur). La phrase unique disait « le moteur ne sait pas dérouler ce
            type » : factuellement fausse depuis, et affichée à l'organisateur la veille du tournoi,
            sur l'écran fait pour le rassurer. Le lot d'origine fermait le signal honnête (le bandeau
            de réserve) et laissait celui-ci en place. */}
        {!phase.joue ? (
          <span className="deroule__ecart" role="note">
            {' '}
            {MOTEUR_SAIT_JOUER.has(phase.type)
              ? '▲ la simulation ne sait pas encore jouer ce type de phase — le moteur, si : le tournoi réel se déroulera normalement'
              : "▲ le moteur ne sait pas encore dérouler ce type de phase — rien n'a été joué ici"}
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
  minimumExige,
  surMinimumExige,
  effectifSimule,
}: {
  nom: string
  surNom: (valeur: string) => void
  etapes: Etape[]
  surEtapes: (etapes: Etape[]) => void
  minimumExige: string
  surMinimumExige: (valeur: string) => void
  // Traversée jusqu'à `FormulaireEtape` pour l'aperçu de répartition des poules (E05US023). Cet
  // éditeur n'en fait rien lui-même : il le fait passer, comme il fait passer `etapes`.
  effectifSimule: number | null
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
      <div className="formulaire__champ">
        <label className="formulaire__libelle" htmlFor="deroule-minimum-exige">
          Minimum d'inscrits exigé (facultatif)
        </label>
        <input
          id="deroule-minimum-exige"
          inputMode="numeric"
          value={minimumExige}
          onChange={(e) => surMinimumExige(e.target.value)}
        />
        <p className="carte__aide">
          Une règle de club : « pas de tournoi de ce type sous 40 archers ». Laissez vide pour vous
          en tenir au minimum que le déroulé impose de lui-même — vous ne pouvez pas exiger moins
          que lui.
        </p>
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
                effectifSimule={effectifSimule}
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
        effectifSimule={effectifSimule}
      />
    </div>
  )
}

/** Exporté pour ses tests, comme `EffectifMinimum` : la composition d'une étape porte deux
 * garde-fous (profondeur réservée aux tableaux, seuil obligatoire sur un top N) qui ne se
 * vérifient qu'en manipulant le formulaire. */
export function FormulaireEtape({
  etape,
  etapesAmont,
  surValider,
  surAnnuler,
  effectifSimule = null,
}: {
  etape?: Etape
  etapesAmont: Etape[]
  surValider: (etape: Etape) => void
  surAnnuler?: () => void
  // L'effectif que l'écran simule, **descendu jusqu'ici** pour la seule fiche de poules : c'est le
  // CA « la répartition obtenue est montrée avant d'être validée » (E05US023). `null` quand l'écran
  // n'en simule aucun — l'aperçu disparaît alors plutôt que d'annoncer un nombre de poules inventé.
  effectifSimule?: number | null
}) {
  const [type, setType] = useState<TypePhase>(etape?.type ?? 'qualification')
  const [nbVolees, setNbVolees] = useState(String(etape?.bareme?.nb_volees ?? 20))
  const [nbFleches, setNbFleches] = useState(String(etape?.bareme?.nb_fleches_par_volee ?? 3))
  const [effectif, setEffectif] = useState(
    etape?.effectif === null ? '' : String(etape?.effectif ?? ''),
  )
  const [sources, setSources] = useState<Source[]>(etape?.sources ?? [])
  // **Source unique** du réglage de profondeur : le formulaire le détient, `ChoixProfondeur` ne
  // fait que le rendre. Le composant en détenait une copie, et comme il est monté sous condition,
  // un aller-retour de type le réinitialisait sans réinitialiser celle-ci — l'écran affichait
  // « Podium » et la soumission envoyait « classement intégral » (cf. l'en-tête du composant).
  const [profondeur, setProfondeur] = useState(depuisProfondeur(etape?.profondeur ?? null))
  // Même parti que la profondeur, et pour la même raison : `ReglagePoules` est monté sous condition,
  // donc il ne peut pas détenir son propre état sans diverger de celui-ci au premier changement de
  // type. Une seule source, ici.
  const [poules, setPoules] = useState(depuisReglage(etape?.poules ?? null))
  const [bigShootOff, setBigShootOff] = useState(depuisReglageBso(etape?.big_shoot_off ?? null))
  // E05US030, même parti que les deux précédents : l'état vit **ici**, la fiche ne fait que le rendre.
  const [suisse, setSuisse] = useState(depuisReglageSuisse(etape?.suisse ?? null))

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
  const enTableau = TYPES_EN_TABLEAU.includes(type)
  const estPoules = type === 'poules'
  // E05US028, même parti que les poules ligne au-dessus : l'état vit **ici**, pas dans la fiche.
  const estBigShootOff = type === 'big_shoot_off'
  const estSuisse = type === 'suisse'
  const saisieInvalide = volees === undefined || fleches === undefined || effectifLu === undefined
  // Deux conditions de blocage, **un message chacune**. Les fondre ferait afficher au seuil vide le
  // conseil générique « laissez le champ vide pour ne rien déclarer » — l'exact contraire de ce
  // qu'il faut faire, puisqu'un top N sans rang d'arrêt est précisément ce qui est refusé.
  const soumissionBloquee =
    saisieInvalide ||
    (enTableau && !estValide(profondeur)) ||
    (estPoules && !poulesValides(poules)) ||
    (estBigShootOff && !bsoValide(bigShootOff)) ||
    (estSuisse && !suisseValide(suisse))

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
    // Même garde que le barème : une profondeur n'a de sens que sur un tableau. Retyper une phase
    // de tableau en poule **efface** donc le réglage plutôt que de l'envoyer se faire refuser.
    profondeur: enTableau ? (versProfondeur(profondeur) ?? null) : null,
    // Même garde encore : un réglage de poules porté par une élimination directe serait refusé en
    // 422 (`ReglageDePoulesInvalide`). Retyper la phase l'**efface** donc, au lieu de l'envoyer se
    // faire recaler — symétrique exact de la ligne au-dessus.
    poules: estPoules ? (versReglage(poules) ?? null) : null,
    // Même garde encore : un réglage de Big Shoot Off porté par un autre type serait refusé en 422
    // (`ConfigurationBigShootOffInvalide`). Retyper la phase l'**efface** donc. La garde compte
    // davantage ici qu'ailleurs : ce réglage décrit **qui sort**.
    big_shoot_off: estBigShootOff ? (versReglageBso(bigShootOff) ?? null) : null,
    // Même garde encore (E05US030) : un nombre de rondes porté par un autre type serait refusé en
    // 422. Retyper la phase l'**efface** donc, au lieu de l'envoyer se faire recaler.
    suisse: estSuisse ? (versReglageSuisse(suisse) ?? null) : null,
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
          // Comme sur l'écran « Phases » (relevé en 2ᵉ passe : le correctif n'avait été appliqué
          // qu'à un des deux formulaires jumeaux). Ce formulaire n'est jamais démonté entre deux
          // ajouts : sans ce reset, « classement intégral » se reportait en silence sur la phase
          // suivante — deux tableaux de 120 partant à ~616 duels que personne n'a demandés.
          setProfondeur(PROFONDEUR_AU_PRESET)
          // Et le réglage de poules avec, pour la raison exacte donnée juste au-dessus : sans ce
          // reset, « poules de 6, 4 qualifiés » se reporterait en silence sur la phase suivante.
          setPoules(POULES_PAR_DEFAUT)
          setBigShootOff(BIG_SHOOT_OFF_PAR_DEFAUT)
          setSuisse(SUISSE_PAR_DEFAUT)
        }
      }}
    >
      <div className="formulaire__champ">
        {/* Le libellé **enveloppe** son `<select>` (corrigé en E06US006) : il flottait à côté sans
            `htmlFor` ni imbrication, donc ne labellisait rien — un lecteur d'écran annonçait une
            liste anonyme, et le champ n'était pas atteignable par son intitulé. Les autres champs
            de ce formulaire enveloppent déjà, celui-ci était le seul écart. */}
        <label className="formulaire__libelle">
          Type de phase
          <select value={type} onChange={(e) => setType(e.target.value as TypePhase)}>
            {TOUS_LES_TYPES.map((valeur) => (
              <option key={valeur} value={valeur}>
                {LIBELLE_TYPE[valeur]}
              </option>
            ))}
          </select>
        </label>
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

      {enTableau && (
        <ChoixProfondeur
          etat={profondeur}
          surChangement={setProfondeur}
          presetIntegral={type === 'placement'}
        />
      )}

      {estPoules && (
        <ReglagePoules etat={poules} surChangement={setPoules} effectif={effectifSimule} />
      )}

      {estBigShootOff && (
        <ReglageBigShootOff
          etat={bigShootOff}
          surChangement={setBigShootOff}
          effectif={effectifSimule}
        />
      )}

      {estSuisse && (
        // ⚠️ **L'effectif DE L'ÉTAPE d'abord, la simulation en repli** (correctif de revue).
        // Les deux fiches voisines annoncent une *projection* indicative, et l'effectif simulé du
        // déroulé leur suffit. Celle-ci annonce une **borne opposable** : c'est
        // `EtapeDeroule._verifier_rondes_appariables` qui refuse l'étape, et il la vérifie contre
        // `effectif` — le champ que ce formulaire envoie juste à côté, pas contre la simulation.
        // Sans ce correctif, simuler 120 archers puis déclarer une étape à 8 affichait « 119
        // rondes au maximum », feu vert, et l'enregistrement rendait 422 : très exactement le
        // parcours que le CA veut supprimer.
        <ReglageSuisse
          etat={suisse}
          surChangement={setSuisse}
          effectif={effectifLu ?? effectifSimule}
        />
      )}

      <EditeurSources etapesAmont={etapesAmont} sources={sources} surSources={setSources} />

      <div className="formulaire__actions">
        <button type="submit" disabled={soumissionBloquee}>
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
          // Un format neuf n'exige rien : la règle de club se pose ensuite, à la composition.
          { nom, etapes: [], effectif_minimum_exige: null },
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
