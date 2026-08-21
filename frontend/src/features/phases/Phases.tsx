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
  TYPES_ARRETABLES,
  TYPES_EN_TABLEAU,
  TYPES_SANS_CLASSEMENT,
} from '../../shared/phases/catalogue'
import { ChoixProfondeur } from '../../shared/phases/ChoixProfondeur'
import { ReglagePoules } from '../../shared/phases/ReglagePoules'
import { ReglageArrets } from '../../shared/phases/ReglageArrets'
import {
  ARRETS_PAR_DEFAUT,
  depuisEtape as depuisArrets,
  estValide as arretsValides,
  versArrets,
} from '../../shared/phases/arrets'
import { ReglageDecoupage } from '../../shared/phases/ReglageDecoupage'
import { depuisDecoupage, versDecoupage } from '../../shared/phases/decoupage'
import { ReglageSuisse } from '../../shared/phases/ReglageSuisse'
import {
  depuisReglage as depuisReglageSuisse,
  estValide as suisseValide,
  versReglage as versReglageSuisse,
  SUISSE_PAR_DEFAUT,
} from '../../shared/phases/suisse'
import { ReglageBigShootOff } from '../../shared/phases/ReglageBigShootOff'
import {
  depuisReglage as depuisReglageBso,
  estValide as bsoValide,
  versReglage as versReglageBso,
  BIG_SHOOT_OFF_PAR_DEFAUT,
} from '../../shared/phases/bigShootOff'
import { useEtatPoules, useRegenererPlanPoules } from '../poules/hooks'
import { useEtatSuisse, useRegenererPlanSuisse } from '../suisse/hooks'
import { ClassementSuisse } from '../suisse/ClassementSuisse'
import {
  depuisReglage,
  estValide as poulesValides,
  versReglage,
  POULES_PAR_DEFAUT,
} from '../../shared/phases/poules'
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

/** Le geste de **pose du plan de couloirs** d'une phase de poules — action admin.
 *
 * ⚠️ Sans ce composant, tout le placement des poules était **inatteignable depuis le produit** : le
 * domaine, le port, l'adapter, la table `placement_par_bloc` et sa migration existaient, l'endpoint
 * admin aussi, et le hook `useRegenererPlanPoules` n'avait **aucun appelant** (relevé en revue
 * d'E05US023, deux axes indépendamment). La table restait donc vide en toutes circonstances, l'écran
 * de saisie affichait en permanence « le plan n'est pas posé, l'organisateur doit le (re)générer »
 * — en désignant une action que l'application n'offrait pas —, et aucune poule n'avait de couloirs :
 * les archers ne savaient pas sur quelle cible tirer.
 *
 * Calqué sur ses deux jumeaux (`features/duels/Duels.tsx`, `features/placement/Placement.tsx`) :
 * même libellé selon que le plan est vide ou déjà posé, même ton **ambre** pour un refus non
 * bloquant.
 */
function PlanDePoules({ tournoiId, phaseId }: { tournoiId: number; phaseId: number }) {
  const etat = useEtatPoules(tournoiId, phaseId)
  const regenerer = useRegenererPlanPoules(tournoiId, phaseId)

  // Le plan est « vide » quand aucune poule ne porte de bloc. On ne se fie pas aux seuls conflits :
  // une phase sans participant n'a ni poule ni conflit, et « Régénérer » y serait un contresens.
  const poules = etat.data?.poules ?? []
  const planVide = poules.length === 0 || poules.every((poule) => poule.bloc === null)
  const conflits = etat.data?.conflits ?? []

  return (
    <>
      <button
        type="button"
        className={planVide ? undefined : 'bouton--discret'}
        disabled={regenerer.isPending || etat.isPending}
        onClick={() => regenerer.mutate()}
      >
        {planVide ? 'Générer le plan' : 'Régénérer le plan'}
      </button>
      {conflits.length > 0 && (
        <span className="carte__etat carte__etat--alerte" role="status">
          {decrireConflits(conflits)}
        </span>
      )}
      <MessageErreur erreur={regenerer.error} />
    </>
  )
}

/** Le même geste pour une phase au **système suisse** (E05US030) — action admin.
 *
 * ⚠️ **Écrit d'emblée pour ne pas rejouer le défaut d'E05US023**, dont le récit est juste au-dessus :
 * l'endpoint, le port et le hook existaient, et rien ne les appelait — le plan restait vide en
 * toutes circonstances, l'écran de saisie réclamait une action que le produit n'offrait pas, et
 * aucun archer ne savait sur quelle cible tirer. `E05US026` a livré `POST /suisse/plan/…` ; sans ce
 * bouton, la même impasse se serait reproduite à l'identique, un format plus loin.
 *
 * Une différence de fond avec les poules : le suisse pose **un seul bloc** pour toute la phase (une
 * ronde apparie tout le plateau d'un coup), donc « le plan est vide » se lit sur les rencontres et
 * non sur des groupes.
 */
function PlanDeSuisse({ tournoiId, phaseId }: { tournoiId: number; phaseId: number }) {
  const etat = useEtatSuisse(tournoiId, phaseId)
  const regenerer = useRegenererPlanSuisse(tournoiId, phaseId)

  const rencontres = (etat.data?.rondes ?? []).flatMap((ronde) => ronde.rencontres)
  // On ne se fie pas aux seuls conflits : une phase sans participant n'a ni ronde ni conflit, et
  // « Régénérer » y serait un contresens.
  const planVide = rencontres.length === 0 || rencontres.every((r) => r.couloirs === null)
  const conflits = etat.data?.conflits ?? []

  return (
    <>
      <button
        type="button"
        className={planVide ? undefined : 'bouton--discret'}
        disabled={regenerer.isPending || etat.isPending}
        onClick={() => regenerer.mutate()}
      >
        {planVide ? 'Générer le plan' : 'Régénérer le plan'}
      </button>
      {conflits.length > 0 && (
        <span className="carte__etat carte__etat--alerte" role="status">
          {/* ⚠️ **« Bloc » et non « Poule(s) »** (correctif de revue) : `decrireConflits` fige son
              vocabulaire, et un suisse — qui n'a aucune poule, mais un bloc unique — lisait
              « Poule(s) 1 sans couloirs : la salle est trop petite ». Le type avait bien été
              distingué (`ConflitSuisse.groupe` vs `Conflit.poule`), le message pas encore. */}
          {decrireConflits(
            conflits.map((c) => ({ poule: c.groupe, raison: c.raison })),
            'Bloc',
          )}
        </span>
      )}
      <MessageErreur erreur={regenerer.error} />
      {/* CA — « le classement provisoire se lit entre les rondes, **côté organisateur** et
          scoreur ». Il n'était livré qu'au scoreur ; la donnée était déjà là, lue pour le bouton
          ci-dessus, et personne ne l'affichait (relevé en revue). */}
      <ClassementSuisse classement={etat.data?.classement ?? []} rondes={etat.data?.rondes ?? []} />
    </>
  )
}

/** Ce que le plan n'a pas pu poser, **et pourquoi** — la raison vient du serveur, pas d'ici.
 *
 * `salle_pleine` et `sans_rencontre` ne sont rendues qu'au retour d'une pose : en relecture, rien
 * n'est persisté qui dise pourquoi une poule n'a pas de bloc, et le serveur répond alors
 * `non_posee`. C'est exact, et c'est ce qui distingue « vous n'avez pas encore généré » de « votre
 * salle est trop petite » — la première version confondait les deux et invitait l'organisateur à
 * regénérer indéfiniment une salle qui ne pouvait pas grandir.
 */
function decrireConflits(
  conflits: { poule: number; raison: string }[],
  // Le nom du groupe est **paramétrable** depuis E05US030 : le système suisse n'a pas de poules,
  // mais un bloc unique. Défaut inchangé, donc aucun appelant existant ne bouge.
  groupe = 'Poule(s)',
): string {
  // ⚠️ **Groupé par raison, pas globalisé.** Une première version listait tous les numéros puis
  // rendait la raison de plus haute priorité : une poule sans rencontre et une poule qui ne tient
  // pas dans la salle s'annonçaient toutes deux « la salle est trop petite », donc l'organisateur
  // agrandissait sa salle pour un problème qui n'en venait pas (relevé en revue).
  const nonPosee = (n: string) => `${groupe} ${n} sans couloirs : le plan n’est pas posé.`
  const libelles: Record<string, ((numeros: string) => string) | undefined> = {
    salle_pleine: (n) => `${groupe} ${n} sans couloirs : la salle est trop petite.`,
    sans_rencontre: (n) => `${groupe} ${n} sans rencontre à tirer : rien à poser.`,
    non_posee: nonPosee,
  }
  const parRaison = new Map<string, number[]>()
  for (const conflit of conflits) {
    parRaison.set(conflit.raison, [...(parRaison.get(conflit.raison) ?? []), conflit.poule])
  }
  return [...parRaison.entries()]
    .map(([raison, numeros]) => {
      const liste = numeros.join(', ')
      return (libelles[raison] ?? nonPosee)(liste)
    })
    .join(' ')
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
        {/* E05US035 — même place et même raison que le barrage juste au-dessus : la qualification
            n'ouvre jamais `FormulairePhase`, donc un réglage qui n'est pas ici n'est nulle part. */}
        {gereeAilleurs && <ReglageDecoupageDePhase tournoiId={tournoiId} phase={phase} />}
        {phase.type === 'poules' && <PlanDePoules tournoiId={tournoiId} phaseId={phase.id} />}
        {phase.type === 'suisse' && <PlanDeSuisse tournoiId={tournoiId} phaseId={phase.id} />}
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
  // Même parti, même raison (E05US023) : `ReglagePoules` est monté sous condition, donc l'état vit
  // ici. L'écran ne simule aucun effectif — le tournoi a de vrais inscrits, et c'est
  // `GET /api/v1/poules/repartition/...` qui dit la répartition réelle une fois la phase posée.
  const [poules, setPoules] = useState(depuisReglage(phase?.poules ?? null))
  const [bigShootOff, setBigShootOff] = useState(depuisReglageBso(phase?.big_shoot_off ?? null))
  // E05US030, même parti que les deux précédents : l'état vit ici, la fiche ne fait que le rendre.
  const [suisse, setSuisse] = useState(depuisReglageSuisse(phase?.suisse ?? null))
  // E05US033, même parti que les quatre précédents : l'état vit ici, la fiche ne fait que le
  // rendre. ⚠️ Les arrêts se lisent sur l'**étape** et non sur une `Phase` : ils sont de la
  // définition du déroulé (ADR-0076), et `Phase` ne porte volontairement pas ce champ.
  const [arrets, setArrets] = useState(depuisArrets(phase?.arrets))
  // ⚠️ **L'effectif RÉEL du créneau, pour que la borne s'affiche là où elle compte** (correctif de
  // revue). Cet écran passait `effectif={null}`, donc la fiche n'annonçait **aucune** borne — sur
  // le seul écran où « l'effectif du jour » du CA existe vraiment. Et comme `ServiceSuisse.etat`
  // **borne silencieusement à la lecture**, l'organisateur ne l'apprenait pas davantage à
  // l'enregistrement : il voyait simplement moins de rondes le jour J.
  //
  // La donnée est déjà servie par la route publique que `PlanDeSuisse` interroge pour cette même
  // phase — on la relit, on ne la recalcule pas. `null` tant qu'il n'y a pas de phase (création
  // pure) : là, aucun effectif n'existe encore, et annoncer une borne serait l'inventer.
  const etatSuisseDeLaPhase = useEtatSuisse(
    tournoiId,
    phase !== undefined && phase.type === 'suisse' ? phase.id : null,
  )
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
  const estPoules = type === 'poules'
  // E05US028, même parti que les poules ligne au-dessus : l'état vit **ici**, pas dans la fiche.
  const estBigShootOff = type === 'big_shoot_off'
  const estSuisse = type === 'suisse'
  // E05US035 : le découpage en tours n'existe que pour la qualification — c'est le seul format
  // dont le nombre de tours n'est pas déjà porté par sa structure.
  // E05US033 : les types qui annoncent leurs tours, donc les seuls sur lesquels une pause puisse
  // se poser (`TYPES_ARRETABLES`, miroir de la table de **même nom** côté domaine — elle a cessé
  // de dériver de `TYPES_DEROULES` en E05US035, ADR-0093). Le serveur refuse
  // l'arrêt ailleurs (`ArretProgrammeInvalide`, 422) — et comme le `PUT` est une édition **totale**,
  // c'est l'étape entière qui serait refusée, pas seulement le champ.
  // ⚠️ **Pour une qualification, l'arrêtabilité dépend du RÉGLAGE, pas du type** (correctif de
  // revue, E05US035, quatre axes). `TYPES_ARRETABLES` répond « on sait observer son tour » ; une
  // qualification non découpée n'en compte qu'**un**, donc aucune pause n'y a de frontière où
  // tomber — le serveur la refuse désormais, et offrir le champ ferait échouer la soumission
  // **entière** (le `PUT` est une édition totale), ce que cette table est justement écrite « en
  // positif » pour éviter. C'est aussi ce que la fiche de découpage affiche deux blocs plus haut :
  // sans cette ligne, l'écran se contredisait lui-même.
  const arretable =
    TYPES_ARRETABLES.has(type) && (type !== 'qualification' || phase?.decoupage != null)
  const soumissionPossible =
    sources !== 'invalide' &&
    !effectifInvalide &&
    !(enTableau && !estValide(profondeur)) &&
    !(estPoules && !poulesValides(poules)) &&
    !(estBigShootOff && !bsoValide(bigShootOff)) &&
    !(estSuisse && !suisseValide(suisse)) &&
    // E05US033 : le contenu ne se juge que là où il est offert — une phase non arrêtable
    // soumet une liste vide, quoi qu'il reste dans l'état d'édition.
    !(arretable && !arretsValides(arrets))

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
      // Idem pour le réglage de poules (E05US023) : réémis sur une phase de poules, **effacé** dès
      // qu'elle est retypée — le serveur refuserait sinon en 422 `reglage_de_poules_invalide`.
      poules: estPoules ? (versReglage(poules) ?? null) : null,
      // Même garde encore (E05US028) : un réglage de Big Shoot Off porté par un autre type serait
      // refusé en 422. Retyper la phase l'**efface** donc. La garde compte davantage ici
      // qu'ailleurs : ce réglage décrit **qui sort**.
      big_shoot_off: estBigShootOff ? (versReglageBso(bigShootOff) ?? null) : null,
      // Même garde encore (E05US030) : un nombre de rondes porté par un autre type serait refusé en
      // 422 `configuration_suisse_invalide`.
      suisse: estSuisse ? (versReglageSuisse(suisse) ?? null) : null,
      // Même garde encore (E05US033) : un arrêt porté par un type qui n'annonce pas ses tours est
      // refusé en 422 `arret_programme_invalide`. Retyper la phase l'**efface** donc, comme les
      // quatre réglages ci-dessus. ⚠️ C'est une **perte de planning assumée** : l'organisateur qui
      // retype une phase de poules en qualification perd ses pauses. L'alternative — les conserver
      // — ferait échouer l'enregistrement entier avec un message que l'écran ne sait pas rattacher
      // au bon champ, ce qui est pire : il ne pourrait plus enregistrer du tout.
      // Même garde encore (E05US035) : un découpage porté par un autre type serait refusé en 422
      // `decoupage_en_tours_invalide`. Retyper la phase l'**efface** donc, comme ses voisins.
      // ⚠️ `versDecoupage` rend déjà `null` pour un seul tour — « non découpée » est l'état par
      // défaut, et persister `{ nb_tours: 1 }` ferait apparaître un réglage jamais posé.
      // ⚠️ **Toujours `null`, et ce n'est pas un oubli** (E05US035). Ce formulaire ne voit jamais
      // de qualification — elle est « gérée ailleurs » (`gereeAilleurs`) et absente de
      // `TYPES_AJOUTABLES`, donc ni éditable ni créable ici, et le `<select>` ne peut pas y mener.
      // Un découpage n'a de sens que sur une qualification : l'émettre à `null` est donc la valeur
      // **exacte**, pas un effacement. Le vrai réglage vit dans `ReglageDecoupageDePhase`, plus bas.
      decoupage: null,
      arrets: arretable ? (versArrets(arrets) ?? []) : [],
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
          setPoules(POULES_PAR_DEFAUT)
          setBigShootOff(BIG_SHOOT_OFF_PAR_DEFAUT)
          setSuisse(SUISSE_PAR_DEFAUT)
          setArrets(ARRETS_PAR_DEFAUT)
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
        {estPoules && <ReglagePoules etat={poules} surChangement={setPoules} effectif={null} />}
        {estBigShootOff && (
          <ReglageBigShootOff etat={bigShootOff} surChangement={setBigShootOff} effectif={null} />
        )}
        {/* Contrairement à ses deux voisines, cette fiche reçoit un effectif : l'**effectif réel du
            créneau**, lu sur la phase en cours d'édition. Ce n'est pas une simulation — c'est le
            nombre que le moteur opposera le jour J, et il n'y avait aucune raison de le cacher à
            celui qui règle le nombre de rondes. */}
        {estSuisse && (
          <ReglageSuisse
            etat={suisse}
            surChangement={setSuisse}
            effectif={etatSuisseDeLaPhase.data?.effectif ?? null}
            // ⚠️ **La borne vient du serveur ici, pas du miroir** (correctif de 2ᵉ tour) : l'état de
            // la phase la porte déjà (`rondes_maximales`), et `decrireBorneConnue` a été écrite
            // dans ce même lot pour ce cas — recalculer côté client aurait enfreint la règle que le
            // lot venait de poser. Dans l'atelier, au contraire, aucune phase n'existe : le miroir
            // y est le seul recours, et c'est ce qui le justifie.
            maximum={etatSuisseDeLaPhase.data?.rondes_maximales ?? null}
          />
        )}
        {/* E05US033 — montée **sans condition de type**, à la différence des quatre fiches
            ci-dessus, mais pour une autre raison : sur un type non arrêtable la fiche n'offre aucun
            champ et **dit pourquoi**. La cacher laisserait chercher un réglage vu sur la phase
            voisine sans jamais apprendre qu'il n'existe pas ici. */}
        <ReglageArrets etat={arrets} surChangement={setArrets} arretable={arretable} />
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
        // Même raison encore : réémis pour ne pas être effacé par une édition **totale**.
        poules: phase.poules,
        // ⚠️ **E05US033, et c'est un bloquant que la revue a trouvé** (axe adversarial). Ce widget
        // n'est rendu **que sur la qualification** — c'est-à-dire exactement le seul type dont le
        // découpage est licite, et celui que la recette demande de doter d'une pause. Sans ces deux
        // lignes, renseigner « barrage jusqu'au rang 8 » **effaçait tout le planning de journée** de
        // l'étape, sans message et avec un `PUT` qui réussit.
        //
        // C'est la leçon de `barrage_jusqu_au` rejouée dans le widget dont le commentaire ci-dessus
        // la raconte, et elle contredisait la promesse écrite dans le DTO côté serveur (« l'écran
        // doit toujours renvoyer la liste complète, jamais un delta »).
        arrets: phase.arrets,
        // Trou **préexistant** fermé au passage : inoffensif sur la qualification (qui ne porte
        // jamais de réglage de suisse), mais c'était le dernier champ non réémis de ce chemin.
        suisse: phase.suisse,
        // ⚠️ **E05US035, et c'est la TROISIÈME fois que ce widget rejoue la même leçon.** Le
        // commentaire de `barrage_jusqu_au` plus haut la raconte, celui d'`arrets` la raconte une
        // deuxième fois — et `decoupage` est exactement le champ le plus exposé : il ne vit que sur
        // la qualification, c'est-à-dire le seul type que ce widget rend. Sans cette ligne,
        // renseigner « barrage jusqu'au rang 8 » **effaçait le découpage en tours**, donc rendait
        // du même coup inertes toutes les pauses posées dessus — sans message, avec un `PUT` qui
        // réussit. Relevé en me corrigeant, pas par un axe : la revue avait signalé la branche
        // morte, ce chemin-ci était encore un cran plus loin.
        decoupage: phase.decoupage,
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
      {/* DETTE-050 : rendu ad hoc non rallié à `shared/ui/texteErreur` — `error.message` brut. */}
      {modifier.isError && (
        <span className="carte__etat carte__etat--erreur" role="alert">
          {modifier.error.message}
        </span>
      )}
    </div>
  )
}

/** Réglage du **découpage en tours** sur la phase de qualification (E05US035, ADR-0093).
 *
 * ⚠️ **Il vit ici et non dans `FormulairePhase`, et c'est un correctif de revue (axe adversarial).**
 * Le champ y avait d'abord été ajouté sous `{estQualification && …}` — une branche **morte** : la
 * qualification n'ouvre jamais ce formulaire (`gereeAilleurs`) et n'est pas dans `TYPES_AJOUTABLES`.
 * Le réglage central de l'US n'était donc atteignable par **aucun** écran de tournoi : l'organisateur
 * ne pouvait pas découper sa qualification, donc pas y poser de pause, sauf à recomposer tout son
 * déroulé depuis un format de bibliothèque. L'US était inerte là où elle sert.
 *
 * C'est **mot pour mot** le défaut que le commentaire de `ReglageBarrage` juste au-dessus raconte
 * pour E06US003 (« Le trou avait été déplacé, pas fermé ») — rejoué un an après, dans le même
 * fichier, à soixante lignes de son propre récit. Le remède est donc le même, à dessein.
 *
 * Contrôle **réduit au seul découpage** : le `PUT` de phase est une édition totale, donc on réémet
 * tous les autres champs tels que la phase les porte. Rouvrir le formulaire complet sur la
 * qualification risquerait d'écraser son barème par surprise — la raison même pour laquelle elle
 * est « gérée ailleurs ».
 */
function ReglageDecoupageDePhase({ tournoiId, phase }: { tournoiId: number; phase: EtapeDeroule }) {
  const [etat, setEtat] = useState(depuisDecoupage(phase.decoupage))
  const modifier = useModifierPhase(tournoiId)
  const decoupage = versDecoupage(etat)

  const enregistrer = () => {
    if (decoupage === undefined) return
    modifier.mutate({
      phaseId: phase.id,
      config: {
        // Édition **totale** : tout ce qu'on ne réémet pas est effacé. Même liste que
        // `ReglageBarrage`, pour la même raison, et `arrets` en tête — c'est le champ dont
        // l'effacement silencieux coûte le plus cher (un planning de journée saisi ligne à ligne).
        type: phase.type,
        sources: phase.sources,
        effectif: phase.effectif,
        barrage_jusqu_au: phase.barrage_jusqu_au,
        profondeur: phase.profondeur,
        poules: phase.poules,
        big_shoot_off: phase.big_shoot_off,
        suisse: phase.suisse,
        arrets: phase.arrets,
        decoupage,
      },
    })
  }

  return (
    <div className="phase__barrage">
      <ReglageDecoupage etat={etat} surChangement={setEtat} nbVolees={phase.nb_volees} />
      <button
        type="button"
        className="bouton--discret"
        onClick={enregistrer}
        disabled={decoupage === undefined || modifier.isPending}
      >
        Enregistrer le découpage
      </button>
      {/* DETTE-050 : rendu ad hoc non rallié à `shared/ui/texteErreur` — `error.message` brut. */}
      {modifier.isError && (
        <span className="carte__etat carte__etat--erreur" role="alert">
          {modifier.error.message}
        </span>
      )}
    </div>
  )
}
