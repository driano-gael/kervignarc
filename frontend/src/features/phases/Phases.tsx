// Séquence de phases d'un tournoi (E05US001, ADR-0045) — réservée à l'admin (`estAdmin`).
//
// Compose la suite ordonnée des phases : ajouter, typer, déclarer une **source** et un
// **effectif**, réordonner, supprimer, piloter le cycle de vie. La cohérence est vérifiée par le
// serveur : ses refus s'affichent tels quels (422/409). La **qualification** apparaît dans la liste
// mais se règle ailleurs. ⚠️ Une phase porte **plusieurs** prélèvements (E05US010) : cet écran les
// affiche tous mais n'en **édite** qu'un, « par rangs » — toute phase hors de ce cas reste en
// lecture (`editableIci`), la soumettre écraserait sa composition sans le dire.

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
  TYPES_A_PLAN_PAR_BLOCS,
  TYPES_ARRETABLES,
  TYPES_EN_TABLEAU,
  TYPES_SANS_CLASSEMENT,
} from '../../shared/phases/catalogue'
import { ChoixProfondeur } from '../../shared/phases/ChoixProfondeur'
import { ReglagePoules } from '../../shared/phases/ReglagePoules'
import { ChampTitre } from '../../shared/phases/ChampTitre'
import { ReglageArrets } from '../../shared/phases/ReglageArrets'
import {
  ARRETS_PAR_DEFAUT,
  depuisEtape as depuisArrets,
  estValide as arretsValides,
  versArrets,
} from '../../shared/phases/arrets'
import { ReglageDecoupage } from '../../shared/phases/ReglageDecoupage'
import { depuisDecoupage, versDecoupage } from '../../shared/phases/decoupage'
import { ReglageColline } from '../../shared/phases/ReglageColline'
import {
  depuisReglage as depuisReglageColline,
  estValide as collineValide,
  porteeMaximale,
  versReglage as versReglageColline,
} from '../../shared/phases/colline'
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
import { useEtatColline, useRegenererPlanColline } from '../colline/hooks'
import { ClassementColline } from '../colline/ClassementColline'
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
 * ⚠️ Sans ce composant, tout le placement des poules était **inatteignable depuis le produit** :
 * domaine, port, adapter, table, migration et endpoint existaient, et `useRegenererPlanPoules`
 * n'avait **aucun appelant** (relevé en revue d'E05US023). La table restait vide, l'écran de saisie
 * réclamait une action que l'application n'offrait pas, et aucune poule n'avait de couloirs.
 * Calqué sur ses deux jumeaux (`duels/Duels.tsx`, `placement/Placement.tsx`).
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
 * ⚠️ **Écrit d'emblée pour ne pas rejouer le défaut d'E05US023**, raconté juste au-dessus :
 * l'endpoint, le port et le hook existaient et rien ne les appelait. Sans ce bouton, la même
 * impasse se serait reproduite à l'identique, un format plus loin. Différence de fond avec les
 * poules : le suisse pose **un seul bloc** pour toute la phase, donc « le plan est vide » se lit
 * sur les rencontres et non sur des groupes.
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

/** Le plan de cibles d'une colline, et la colline elle-même — **côté organisateur**.
 *
 * ⚠️ **3ᵉ récidive du même défaut** (E05US023 poules, puis suisse) : le hook, la route et le
 * service existaient, et rien ne les appelait — `_plan_suffisant` rendait `False` en permanence et
 * personne ne savait sur quelle cible tirer. Le commentaire a tenu pour le suisse et pas ici : un
 * avertissement en prose ne se déclenche pas, le garde-fou réel est le test de rendu ci-joint.
 * Comme le suisse : **un seul bloc**, donc `decrireConflits(..., 'Bloc')`.
 */
function PlanDeColline({ tournoiId, phaseId }: { tournoiId: number; phaseId: number }) {
  const etat = useEtatColline(tournoiId, phaseId)
  const regenerer = useRegenererPlanColline(tournoiId, phaseId)

  // Même garde que chez le suisse : une phase sans participant n'a ni défi ni conflit, et
  // « Régénérer » y serait un contresens.
  const defis = (etat.data?.manches ?? []).flatMap((manche) => manche.defis)
  const planVide = defis.length === 0 || defis.every((defi) => defi.couloirs === null)
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
          {decrireConflits(
            conflits.map((c) => ({ poule: c.groupe, raison: c.raison })),
            'Bloc',
          )}
        </span>
      )}
      <MessageErreur erreur={regenerer.error} />
      {/* La colline **est** le classement : l'organisateur le lit ici sans un appel de plus, la
          donnée étant déjà chargée pour le bouton ci-dessus. Même geste qu'`ClassementSuisse`. */}
      <ClassementColline
        classement={etat.data?.classement ?? []}
        manches={etat.data?.manches ?? []}
      />
    </>
  )
}

/** Ce que le plan n'a pas pu poser, **et pourquoi** — la raison vient du serveur, pas d'ici.
 *
 * `salle_pleine` et `sans_rencontre` ne sont rendues qu'au retour d'une pose ; en relecture le
 * serveur répond `non_posee`. ⚠️ C'est ce qui distingue « vous n'avez pas encore généré » de
 * « votre salle est trop petite » — la première version confondait les deux et invitait à
 * regénérer indéfiniment une salle qui ne pouvait pas grandir.
 */

/** Aiguille vers le panneau de plan du format — un seul point d'entrée, dérivé de la table.
 *
 * Les trois panneaux restent distincts (`DETTE-079`) ; ce qui est centralisé ici, c'est le **fait
 * qu'un type en ait un**, seule chose que le garde-fou peut vérifier mécaniquement.
 */
function PlanParBlocs({
  type,
  tournoiId,
  phaseId,
}: {
  type: TypePhase
  tournoiId: number
  phaseId: number
}) {
  if (type === 'poules') return <PlanDePoules tournoiId={tournoiId} phaseId={phaseId} />
  if (type === 'suisse') return <PlanDeSuisse tournoiId={tournoiId} phaseId={phaseId} />
  if (type === 'colline') return <PlanDeColline tournoiId={tournoiId} phaseId={phaseId} />
  // Un type entré dans `TYPES_A_PLAN_PAR_BLOCS` sans panneau : le test le voit, l'écran ne ment pas.
  return null
}

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
  // ⚠️ **Une seule bascule par ligne, pour tous les types** (E16US002). L'écran offrait avant un
  // « Éditer » réservé aux types composables, et posait les réglages de la qualification (barrage,
  // découpage) **à plat dans la barre d'actions** — d'où le refus A07 (« la gestion d'une phase
  // demande des écrans plus détaillés »). La fiche est désormais le seul endroit où l'on règle une
  // phase, quel que soit son type.
  const [ficheOuverte, setFicheOuverte] = useState(false)
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

  return (
    <li className="phase">
      <div className="phase__ligne">
        <span className="phase__ordre">{phase.ordre}</span>
        {/* Le **titre** identifie la phase, le type la classe : quand l'organisateur a nommé sa
            phase, c'est son nom qu'il cherche du regard. Sans titre, le libellé du type reprend
            exactement la place qu'il occupait — aucun déroulé existant ne change d'aspect. */}
        <span className="phase__type">{phase.titre ?? LIBELLE_TYPE[phase.type]}</span>
        <span className="phase__details">
          {/* Le type n'est jamais perdu : il redevient un détail, il ne disparaît pas. Sans lui,
              deux phases nommées ne diraient plus ce qu'elles font. */}
          {phase.titre != null && `${LIBELLE_TYPE[phase.type]} · `}
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
        {/* ⚠️ **Le montage dérive de `TYPES_A_PLAN_PAR_BLOCS`, et ce n'est pas cosmétique.** Trois
            fois de suite, un format a gagné son plan de cibles côté serveur sans que personne ne
            monte l'appelant ici — et le format devenait injouable, faute de couloirs. Passer par la
            table déplace la récidive du montage vers la table : un type ajouté là-bas et absent de
            ce `switch` fait rougir `PlansDeCibles.test.tsx`, qui itère sur la même table. */}
        {TYPES_A_PLAN_PAR_BLOCS.has(phase.type) && (
          <PlanParBlocs type={phase.type} tournoiId={tournoiId} phaseId={phase.id} />
        )}
        {/* ⚠️ **Offerte même sur la qualification**, qui n'avait aucune bascule : ses réglages
            traînaient dans cette barre d'actions. Le refus « composition avancée » ne porte, lui,
            que sur l'**édition de séquence** — pas sur la fiche, dont le titre reste réglable. */}
        <button
          type="button"
          className="bouton--discret"
          aria-expanded={ficheOuverte}
          onClick={() => setFicheOuverte((ouverte) => !ouverte)}
        >
          {ficheOuverte ? 'Fermer la fiche' : 'Ouvrir la fiche'}
        </button>
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
      {ficheOuverte && (
        <div className="phase__fiche">
          {gereeAilleurs ? (
            <>
              {/* La qualification n'ouvre jamais `FormulairePhase` — son barème se règle sur
                  « Barème & validation », et l'éditer ici le perdrait par surprise. Sa fiche est
                  donc composée de ses réglages propres, réunis au même endroit que ceux des
                  autres types au lieu d'être dispersés dans la barre d'actions. */}
              <ReglageTitre tournoiId={tournoiId} phase={phase} />
              <ReglageBarrage tournoiId={tournoiId} phase={phase} />
              <ReglageDecoupageDePhase tournoiId={tournoiId} phase={phase} />
            </>
          ) : editableIci(phase.sources) ? (
            <FormulairePhase
              tournoiId={tournoiId}
              phases={phases}
              phase={phase}
              onTermine={() => setFicheOuverte(false)}
            />
          ) : (
            <>
              {/* Composition avancée : la **séquence** ne s'édite pas ici (plusieurs sources, ou
                  une source que ce formulaire ne sait pas exprimer). Le **titre**, lui, n'a rien à
                  voir avec la séquence — le refuser aussi rendrait ces phases-là impossibles à
                  nommer, alors que ce sont justement les déroulés les plus fournis. */}
              <ReglageTitre tournoiId={tournoiId} phase={phase} />
              {/* ⚠️ **Message corrigé au passage (E16US002), il était trompeur.** Il disait
                  « éditable depuis l'écran de composition du déroulé » et désignait l'atelier —
                  qui ne travaille sur **aucun tournoi** (ADR-0063) et ne pouvait donc pas éditer
                  cette phase-ci. Le renommage des deux destinations l'a mis à nu : recopier
                  l'ancienne phrase avec le nouveau nom aurait conservé le cul-de-sac. Le vrai
                  chemin passe par un format, puis par son assemblage sur le tournoi. */}
              <span className="carte__etat" role="note">
                Composition avancée : cette phase porte plusieurs prélèvements, que ce formulaire ne
                sait pas éditer. Pour la recomposer, préparez un format (« Composer un format »)
                puis appliquez-le depuis « Assemblage ».
              </span>
            </>
          )}
        </div>
      )}
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
  // E16US002 — le libellé libre de l'étape. Pas de normalisation ici : le domaine strippe et ramène
  // le blanc à `null` (`_titre_normalise`), et normaliser aussi côté client ferait deux règles pour
  // une même donnée — à faire diverger au premier ajustement.
  // DETTE-080 — 10ᵉ réglage dont l'état, la garde de type et le reset sont écrits **deux fois**,
  // ici et dans le formulaire jumeau de « Composer un format ». Les contrôles, eux, sont partagés
  // (`shared/phases/`) : c'est la plomberie autour d'eux qui se recopie.
  const [titre, setTitre] = useState(phase?.titre ?? '')
  const [effectif, setEffectif] = useState(phase?.effectif != null ? String(phase.effectif) : '')
  // **Source unique** du réglage de profondeur (E06US006), détenue ici et non dans le contrôle :
  // celui-ci est monté sous condition, donc une copie interne divergerait au premier aller-retour
  // de type. Le contrôle est partagé avec « Composer un format » — le réglage y a le même sens.
  const [profondeur, setProfondeur] = useState(depuisProfondeur(phase?.profondeur ?? null))
  // Même parti, même raison (E05US023) : `ReglagePoules` est monté sous condition, donc l'état vit
  // ici. L'écran ne simule aucun effectif — le tournoi a de vrais inscrits, et c'est
  // `GET /api/v1/poules/repartition/...` qui dit la répartition réelle une fois la phase posée.
  const [poules, setPoules] = useState(depuisReglage(phase?.poules ?? null))
  const [bigShootOff, setBigShootOff] = useState(depuisReglageBso(phase?.big_shoot_off ?? null))
  // E05US030, même parti que les deux précédents : l'état vit ici, la fiche ne fait que le rendre.
  const [suisse, setSuisse] = useState(depuisReglageSuisse(phase?.suisse ?? null))
  // E05US027, même parti que les précédents : l'état vit ici, la fiche ne fait que le rendre.
  const [colline, setColline] = useState(depuisReglageColline(phase?.colline ?? null))
  // E05US033, même parti que les quatre précédents : l'état vit ici, la fiche ne fait que le
  // rendre. ⚠️ Les arrêts se lisent sur l'**étape** et non sur une `Phase` : ils sont de la
  // définition du déroulé (ADR-0076), et `Phase` ne porte volontairement pas ce champ.
  const [arrets, setArrets] = useState(depuisArrets(phase?.arrets))
  // ⚠️ **L'effectif RÉEL du créneau, pour que la borne s'affiche là où elle compte** (correctif de
  // revue). Cet écran passait `effectif={null}`, donc aucune borne n'était annoncée — sur le seul
  // écran où « l'effectif du jour » du CA existe. Et comme `ServiceSuisse.etat` **borne
  // silencieusement à la lecture**, l'organisateur voyait simplement moins de rondes le jour J.
  // La donnée vient de la route publique que `PlanDeSuisse` interroge déjà ; `null` tant qu'il n'y
  // a pas de phase — annoncer une borne y serait l'inventer.
  const etatSuisseDeLaPhase = useEtatSuisse(
    tournoiId,
    phase !== undefined && phase.type === 'suisse' ? phase.id : null,
  )
  // ⚠️ **Même geste que pour le suisse juste au-dessus, et pour la même raison** : l'effectif réel
  // du créneau est le seul endroit où « l'effectif du jour » du CA existe vraiment, et le service
  // **borne silencieusement à la lecture** — sans cette annonce, l'organisateur qui règle une
  // portée trop grande ne l'apprend ni à l'enregistrement ni le jour J, il voit simplement des
  // défis plus courts que prévu.
  const etatCollineDeLaPhase = useEtatColline(
    tournoiId,
    phase !== undefined && phase.type === 'colline' ? phase.id : null,
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

  // Sources possibles : les phases **antérieures** qui produisent un classement. ⚠️ Le filtre sur
  // les phases non classantes n'est pas cosmétique : ce formulaire ne sait exprimer que le
  // prélèvement « par rangs », et le serveur refuse de prélever des rangs dans un échauffement.
  // Sans lui, l'organisateur reçoit un 422 dont la consigne — « reprendre le reste » — n'est
  // réalisable par aucun écran : une impasse sans sortie. Le chemin réel reste ouvert (une phase
  // peut n'avoir aucune source) ; la saisie du prélèvement « le reste » arrive avec E01US024.
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
  const estColline = type === 'colline'
  // E05US035 : le découpage en tours n'existe que pour la qualification. E05US033 :
  // `TYPES_ARRETABLES` (miroir de la table de même nom côté domaine, ADR-0093) dit quels types
  // annoncent leurs tours, donc où une pause peut se poser. ⚠️ **Pour une qualification,
  // l'arrêtabilité dépend du RÉGLAGE, pas du type** : non découpée, elle n'a qu'un tour, aucune
  // frontière où poser une pause, et le `PUT` étant une édition **totale** c'est la soumission
  // entière qui échouerait. ⚠️ Pas de condition sur le découpage ici : ce formulaire ne voit jamais
  // de qualification, la garde d'instance vit dans `ReglageDecoupageDePhase`. ⚠️ `Number('4a')`
  // rend `NaN` et `??` ne le filtre pas — d'où la normalisation (le champ est du texte libre).
  const effectifRetenu = effectifInvalide ? null : effectifAnalyse
  const arretable = TYPES_ARRETABLES.has(type)
  const soumissionPossible =
    sources !== 'invalide' &&
    !effectifInvalide &&
    !(enTableau && !estValide(profondeur)) &&
    !(estPoules && !poulesValides(poules)) &&
    !(estBigShootOff && !bsoValide(bigShootOff)) &&
    !(estSuisse && !suisseValide(suisse)) &&
    !(estColline && !collineValide(colline)) &&
    // ⚠️ **La borne d'effectif est OPPOSABLE, donc elle doit désactiver le bouton** (correctif de
    // 2ᵉ passe). `collineValide` ne juge que les bornes absolues du réglage (1..64) ; la borne qui
    // dépend de l'effectif déclaré, elle, est celle que `EtapeDeroule._verifier_portee_de_defi`
    // **refuse** en 422. Sans cette ligne, l'écran disait la borne, laissait « Enregistrer » actif,
    // et le serveur refusait — la moitié du parcours que le CA veut supprimer restait ouverte.
    !(
      estColline &&
      effectifRetenu !== null &&
      (versReglageColline(colline)?.portee_de_defi ?? 0) > porteeMaximale(effectifRetenu)
    ) &&
    // E05US033 : le contenu ne se juge que là où il est offert — une phase non arrêtable
    // soumet une liste vide, quoi qu'il reste dans l'état d'édition.
    !(arretable && !arretsValides(arrets))

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!soumissionPossible) return
    // ⚠️ `barrage_jusqu_au` est **réémis tel quel** : le `PUT` est une édition **totale**, donc
    // l'omettre effacerait le seuil dès qu'on corrige un effectif. Il ne se **règle** pas ici (voir
    // `ReglageBarrage`, sur la qualification), il se **préserve**.
    // ⚠️ **`Required` ici aussi, et c'est le chemin MAJORITAIRE** (relevé en 2ᵉ passe). Le
    // garde-fou avait d'abord été posé sur `configInchangee`, qui ne sert que les widgets à champ
    // unique, en laissant sans garde le formulaire qui écrit toute création de phase et toute
    // édition d'un type composable. Le trou n'était pas fermé, il était déplacé vers l'écrivain
    // le plus fréquent.
    const config: Required<ConfigPhase> = {
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
      // Même garde encore (E05US027) : un réglage de colline porté par un autre type serait refusé
      // en 422 `configuration_colline_invalide`. Retyper la phase l'**efface** donc.
      colline: estColline ? (versReglageColline(colline) ?? null) : null,
      // Retyper la phase **efface** l'arrêt (E05US033) et le découpage (E05US035), comme les
      // quatre autres réglages : portés par un autre type, ils seraient refusés en 422 et le `PUT`
      // étant total, c'est l'enregistrement entier qui échouerait. ⚠️ **Perte de planning
      // assumée** — conserver les pauses rendrait l'écran impossible à enregistrer, ce qui est
      // pire. ⚠️ `versDecoupage` rend déjà `null` pour un seul tour. Le `null` **en dur** a été
      // écarté : le `<select>` accepte un type hors catalogue, donc le jour où la qualification y
      // deviendrait éditable la constante effacerait son découpage en silence — 4ᵉ occurrence de
      // la leçon que ce fichier raconte déjà trois fois. Deux caractères l'empêchent.
      decoupage: type === 'qualification' ? (phase?.decoupage ?? null) : null,
      arrets: arretable ? (versArrets(arrets) ?? []) : [],
      // E16US002 : vidé = titre **retiré**, l'écran retombe sur le libellé du type. Contrairement
      // aux cinq réglages ci-dessus, il n'est **pas** effacé par un retypage : un titre n'appartient
      // à aucun type, et « Tableau des jeunes » reste juste si la phase devient des poules.
      titre: titre.trim() === '' ? null : titre,
    }
    if (enEdition) {
      modifier.mutate({ phaseId: phase.id, config }, { onSuccess: onTermine })
    } else {
      ajouter.mutate(config, {
        onSuccess: () => {
          setEffectif('')
          setTitre('')
          // La profondeur se remet au preset comme les autres champs : « classement intégral »
          // est le réglage le plus coûteux de la journée, il ne doit pas se reporter en silence
          // d'une phase à la suivante.
          //
          // ⚠️ Ce commentaire disait « l'atelier ne réinitialise AUCUN champ » : périmé depuis
          // E06US006 — il en réinitialise **sept**. L'asymétrie est réelle mais partielle, et
          // `DETTE-080` s'était sourcée sur cette phrase plutôt que sur le code.
          setProfondeur(PROFONDEUR_AU_PRESET)
          setPoules(POULES_PAR_DEFAUT)
          setBigShootOff(BIG_SHOOT_OFF_PAR_DEFAUT)
          setSuisse(SUISSE_PAR_DEFAUT)
          // Relevé en 2ᵉ passe de revue : la colline manquait à cette liste, à rebours du
          // raisonnement ci-dessus — un Ladder portée 4 sur 8 manches se serait reporté en silence
          // sur la phase suivante, alors que c'est un choix de format, pas une préférence.
          setColline(depuisReglageColline(null))
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
        {/* En tête de fiche parce que c'est ce que le CA nomme en premier (« sa fiche, qui reprend
            son titre et ses réglages ») — et parce que c'est le champ qui identifie la phase pour
            l'organisateur, là où le type ne fait que la classer. */}
        <ChampTitre
          valeur={titre}
          surChangement={setTitre}
          libelle="Titre de la phase (facultatif)"
          placeholder={LIBELLE_TYPE[type]}
        />
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
            // ⚠️ **Même geste que la colline dix lignes plus bas, et il manquait ici** (relevé
            // en 2ᵉ passe). `EtapeDeroule._verifier_rondes_appariables` juge lui aussi contre
            // `self.effectif`, c'est-à-dire le champ saisi sur cet écran. Corriger la colline en
            // laissant le suisse aurait été un trou **déplacé** — exactement ce que la 1ʳᵉ passe
            // avait relevé trois fois, reproduit dans le commit qui prétendait le fermer.
            effectif={effectifRetenu ?? etatSuisseDeLaPhase.data?.effectif ?? null}
            // ⚠️ **La borne vient du serveur ici, pas du miroir** (correctif de 2ᵉ tour) : l'état de
            // la phase la porte déjà (`rondes_maximales`), et `decrireBorneConnue` a été écrite
            // dans ce même lot pour ce cas — recalculer côté client aurait enfreint la règle que le
            // lot venait de poser. Dans l'atelier, au contraire, aucune phase n'existe : le miroir
            // y est le seul recours, et c'est ce qui le justifie.
            maximum={
              effectifRetenu !== null ? null : (etatSuisseDeLaPhase.data?.rondes_maximales ?? null)
            }
          />
        )}
        {estColline && (
          <ReglageColline
            etat={colline}
            surChangement={setColline}
            // ⚠️ **L'effectif DÉCLARÉ d'abord, le prélevé en repli** (correctif de revue). La
            // borne annoncée doit être celle que le serveur **oppose** :
            // `_verifier_portee_de_defi` refuse l'étape contre `self.effectif`, le champ saisi
            // trois blocs plus haut et envoyé dans la même requête — pas contre la population déjà
            // prélevée. Sans ça : 40 inscrits, phase déclarée à 4, portée 5 → « 40 archers : au
            // plus 39 rangs », feu vert, et l'enregistrement rendait 422.
            effectif={effectifRetenu ?? etatCollineDeLaPhase.data?.effectif ?? null}
            // La borne serveur ne vaut que tant qu'aucun effectif n'est déclaré : sinon elle
            // écraserait la borne de l'effectif saisi, ce qui rouvrirait le défaut ci-dessus par
            // l'autre bout. `ReglageColline` retombe alors sur `effectif`.
            maximum={
              effectifRetenu !== null ? null : (etatCollineDeLaPhase.data?.portee_maximale ?? null)
            }
          />
        )}
        {/* E05US033 — montée **sans condition de type**, à la différence des cinq fiches
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
                  {/* Le sélecteur restait anonyme alors que la ligne juste au-dessus est titrée
                      (correctif de revue) : choisir sa source parmi trois « Qualification » est le
                      geste que le titre doit précisément rendre possible. */}
                  Phase {p.ordre} — {p.titre ?? LIBELLE_TYPE[p.type]}
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
 * ⚠️ **Il vit ici et nulle part ailleurs, et c'est un correctif de revue** : le champ avait été
 * ajouté à `FormulairePhase`, que la qualification **n'ouvre jamais** — le seuil restait réglable
 * par aucun écran. Contrôle **réduit au seul seuil** : le `PUT` étant une édition totale, on
 * réémet le reste tel quel ; rouvrir le formulaire complet risquerait d'écraser son barème.
 */

/** La config **complète et inchangée** d'une étape, à surcharger par le seul champ qu'on édite.
 *
 * ⚠️ **Extrait sur preuve** : le `PUT` est une édition **totale**, tout champ non réémis est
 * effacé. Ce fichier raconte trois effacements nés d'une recopie incomplète. ⚠️ Le type de retour
 * est `Required<ConfigPhase>`, et c'est **lui** le garde-fou : sans lui, un 13ᵉ réglage oublié ici
 * compilerait sans un mot. ⚠️ `nb_volees` est délibérément absent — champ de lecture seule, et ce
 * routeur est le seul du projet en `extra="forbid"`.
 */
function configInchangee(phase: EtapeDeroule): Required<ConfigPhase> {
  // DETTE-080 — la config est recopiée depuis la **prop**, qui reste périmée jusqu'au refetch de
  // React Query. Trois widgets d'édition totale cohabitent dans la fiche : enregistrer deux d'entre
  // eux coup sur coup peut réécrire la valeur du premier. Assumé (fenêtre d'un aller-retour LAN),
  // inscrit au registre avec son remède borné.
  return {
    type: phase.type,
    sources: phase.sources,
    effectif: phase.effectif,
    barrage_jusqu_au: phase.barrage_jusqu_au,
    profondeur: phase.profondeur,
    poules: phase.poules,
    big_shoot_off: phase.big_shoot_off,
    suisse: phase.suisse,
    colline: phase.colline,
    decoupage: phase.decoupage,
    arrets: phase.arrets,
    titre: phase.titre,
  }
}

/** Édite le seul **titre** d'une étape (E16US002), sans toucher au reste de sa définition.
 *
 * Monté dans la fiche de la **qualification**, qui n'ouvre jamais `FormulairePhase` : son barème se
 * règle ailleurs, et l'y éditer le ferait perdre par surprise (`gereeAilleurs`). Sans ce widget, la
 * qualification serait le seul type impossible à nommer — précisément celui dont le CA dit qu'on
 * peut en avoir plusieurs.
 */
function ReglageTitre({ tournoiId, phase }: { tournoiId: number; phase: EtapeDeroule }) {
  const [valeur, setValeur] = useState(phase.titre ?? '')
  const modifier = useModifierPhase(tournoiId)

  return (
    <div className="phase__reglage">
      <ChampTitre
        valeur={valeur}
        surChangement={setValeur}
        libelle="Titre de la phase (facultatif)"
        placeholder={LIBELLE_TYPE[phase.type]}
      />
      <button
        type="button"
        className="bouton--discret"
        disabled={modifier.isPending}
        onClick={() =>
          modifier.mutate({
            phaseId: phase.id,
            // Vidé = titre retiré : c'est le geste par lequel on revient au libellé du type.
            config: { ...configInchangee(phase), titre: valeur.trim() === '' ? null : valeur },
          })
        }
      >
        Enregistrer
      </button>
      <span className="carte__aide">
        Vide = le type sert de libellé. Utile quand le déroulé porte plusieurs phases du même type.
      </span>
      {/* DETTE-050 : rendu ad hoc non rallié à `shared/ui/texteErreur`, comme ses voisins. */}
      {modifier.isError && (
        <span className="carte__etat carte__etat--erreur" role="alert">
          {modifier.error.message}
        </span>
      )}
    </div>
  )
}

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
        // Édition **totale** : tout champ non réémis est effacé. `configInchangee` porte la liste
        // et la raison — deux bugs sont nés de la recopie à la main qui vivait ici, dont
        // l'effacement du `decoupage` (et l'inertie des pauses posées dessus) par ce widget même.
        ...configInchangee(phase),
        barrage_jusqu_au: analyse,
      },
    })
  }

  return (
    <div className="phase__reglage">
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
 * ⚠️ **Il vit ici et non dans `FormulairePhase`** (correctif de revue, axe adversarial) : le champ
 * y était sous une branche **morte**, la qualification n'ouvrant jamais ce formulaire. Le réglage
 * central de l'US n'était atteignable par aucun écran. C'est **mot pour mot** le défaut que
 * `ReglageBarrage` raconte soixante lignes plus haut, rejoué un an après dans le même fichier.
 * Contrôle **réduit au seul découpage**, pour la même raison que là-bas.
 */
function ReglageDecoupageDePhase({ tournoiId, phase }: { tournoiId: number; phase: EtapeDeroule }) {
  const [etat, setEtat] = useState(depuisDecoupage(phase.decoupage))
  const [arrets, setArrets] = useState(depuisArrets(phase.arrets))
  const modifier = useModifierPhase(tournoiId)
  const decoupage = versDecoupage(etat)
  // Une pause ne peut se poser que sur une qualification **découpée**, et la condition se lit sur
  // l'état en cours de saisie : taper « 2 » doit ouvrir la fiche immédiatement, sans enregistrer.
  const arretable = decoupage !== undefined && decoupage !== null
  const pausesPerdues = !arretable ? arrets.lignes.length : 0

  const enregistrer = () => {
    if (decoupage === undefined || (arretable && !arretsValides(arrets))) return
    modifier.mutate({
      phaseId: phase.id,
      config: {
        ...configInchangee(phase),
        // ⚠️ **Les pauses suivent le découpage, et ce n'est pas un choix esthétique** (correctif de
        // 2ᵉ passe de revue). Réémettre `phase.arrets` tels quels en ramenant le découpage à 1 tour
        // faisait **refuser l'enregistrement en 422**, avec un message qui conseille exactement
        // l'inverse du geste en cours (« Découpez d'abord la qualification… ») : un cul-de-sac,
        // puisque c'est le seul écran d'où l'organisateur peut agir. L'effacement est donc explicite
        // — et **annoncé avant** le clic, parce qu'un planning de journée saisi ligne à ligne ne
        // disparaît pas en silence (c'est ce que le DTO serveur exige de cet écran).
        arrets: arretable ? (versArrets(arrets) ?? []) : [],
        decoupage,
      },
    })
  }

  return (
    <div className="phase__reglage">
      <ReglageDecoupage etat={etat} surChangement={setEtat} nbVolees={phase.nb_volees} />
      {/* ⚠️ **Montée ICI et pas dans `FormulairePhase`, pour la même raison que le découpage
          lui-même** — et c'est un bloquant de 2ᵉ passe : le premier correctif avait fermé la moitié
          `decoupage` du trou de câblage et laissé la moitié `arrets` ouverte. La qualification
          pouvait donc être découpée mais ne pouvait porter aucune pause, c'est-à-dire que l'US
          restait inerte sur le geste même pour lequel le découpage existe. Les deux réglages vont
          ensemble : le découpage n'a pas d'autre raison d'être. */}
      <ReglageArrets
        etat={arrets}
        surChangement={setArrets}
        arretable={arretable}
        motif="non-decoupee"
      />
      {pausesPerdues > 0 && (
        <span className="carte__etat carte__etat--alerte" role="status">
          Ramener cette qualification à un seul tour supprimera{' '}
          {pausesPerdues > 1 ? `les ${pausesPerdues} pauses programmées` : 'la pause programmée'} de
          cette phase.
        </span>
      )}
      <button
        type="button"
        className="bouton--discret"
        onClick={enregistrer}
        disabled={
          decoupage === undefined || (arretable && !arretsValides(arrets)) || modifier.isPending
        }
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
