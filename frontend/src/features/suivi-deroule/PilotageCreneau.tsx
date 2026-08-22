// Pilotage du déroulé **dans un créneau** (E01US025, ADR-0076) — axe pilotage, poste admin.
//
// **Pourquoi ce panneau existe.** Jusqu'à ADR-0076, l'écran « Phases » portait les deux mailles :
// on y composait la séquence *et* on la faisait vivre, parce qu'un tournoi n'avait qu'une suite de
// phases. Depuis, le déroulé est défini **une fois** au tournoi et chaque départ le rejoue : « la
// phase 2 » ne désigne plus un objet mais N avancements, un par créneau. Un bouton « Démarrer »
// sur le déroulé n'aurait donc plus de destinataire — démarrer *où* ? Le geste descend ici, à la
// maille qui a un statut, et l'écran « Phases » redevient un atelier de composition.
//
// **Pourquoi ici et pas dans un écran neuf.** « Suivi du déroulé » est déjà la destination de l'axe
// pilotage : l'organisateur y lit où en est son tournoi. Lui faire changer d'écran pour agir sur ce
// qu'il vient de lire serait une couture inutile. Le schéma reste la vue d'ensemble du tournoi ; ce
// panneau est la commande, créneau par créneau.
//
// ⚠️ Ce module n'est **pas** monté sur l'écran de salle (`EcranSalle` compose sa propre vue à partir
// des mêmes hooks) : « aucune interaction » y reste vrai, CA E07US004.

import { useState } from 'react'

import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useMaintenant } from '../../shared/ui/useMaintenant'
import { LIBELLE_TYPE } from '../../shared/phases/catalogue'
import {
  libelleEtatDuTour,
  peutPoserUnePause,
  phraseDeRelance,
  resumeDeRelance,
  toursBloquablesRestants,
} from '../../shared/phases/relance'
import type { PorteeArret } from '../../shared/phases/arrets'
import type { AvancementBloc } from '../../shared/schema-braquets/modele'
import type { Phase, StatutPhase, TransitionPhase } from '../phases/api'
import { usePhases, useAvancementPhases, useChangerStatutPhase } from '../phases/hooks'
import {
  useArretsEnAttente,
  usePoserArretRelatif,
  useRelancerArret,
  useSuiviDeroule,
} from './hooks'

const LIBELLE_STATUT: Record<StatutPhase, string> = {
  a_venir: 'À venir',
  en_cours: 'En cours',
  en_pause: 'En pause',
  terminee: 'Terminée',
}

// Transitions offertes selon le statut courant (ADR-0045 §1). Le serveur reste l'autorité (409 si
// l'état a changé entre l'affichage et le clic) — cette table ne fait qu'éviter d'offrir un geste
// dont on sait déjà qu'il sera refusé.
const TRANSITIONS: Record<StatutPhase, { transition: TransitionPhase; libelle: string }[]> = {
  a_venir: [{ transition: 'demarrer', libelle: 'Démarrer' }],
  en_cours: [
    { transition: 'mettre_en_pause', libelle: 'Mettre en pause' },
    { transition: 'terminer', libelle: 'Terminer' },
  ],
  en_pause: [{ transition: 'reprendre', libelle: 'Reprendre' }],
  terminee: [],
}

/** ⚠️ Le créneau est **reçu**, plus choisi ici (E01US025). Le sélecteur a été hissé dans
 * `SuiviDeroule` : le schéma au-dessus est lui aussi celui d’un créneau depuis ADR-0075, et deux
 * sélecteurs sur le même écran laisseraient lire l’avancement du matin sous le dessin de
 * l’après-midi. Un écran, un créneau. */
export function PilotageCreneau({
  tournoiId,
  departId,
  aucunCreneau,
}: {
  tournoiId: number
  departId: number | null
  aucunCreneau: boolean
}) {
  const phases = useAvancementPhases(departId)
  // E05US034 — le **tour** de chaque phase, lu du suivi. Le panneau n'affichait que le statut, ce
  // qui suffisait tant qu'aucun geste ne s'y référait ; « bloquer dans x tours » change cela : on ne
  // demande pas à quelqu'un de compter des tours sans lui dire où il en est. Même clé de requête que
  // le schéma juste au-dessus, donc **aucun appel de plus** — React Query sert le cache partagé.
  const suivi = useSuiviDeroule(departId)
  const avancementParOrdre = new Map(
    (suivi.data?.avancement ?? []).map((bloc) => [bloc.ordre, bloc]),
  )
  // E16US002, correctif de revue (axe adversarial) — **le titre des étapes, joint par `ordre`.**
  //
  // ⚠️ `Phase` (l'avancement dans un créneau) ne porte délibérément pas le titre : il décrit la
  // composition, et le serveur ne le sert que sur `EtapeReponse` (ADR-0095 §3). Mais le laisser
  // hors de CET écran-ci était un défaut, pas une conséquence : c'est ici qu'on **démarre** et
  // qu'on **termine** une phase, donc le seul endroit où confondre deux qualifications homonymes
  // coûte réellement quelque chose — publier le mauvais classement. Livrer « vous pouvez nommer vos
  // phases » en laissant anonyme l'écran du geste, c'était la capacité livrée mais inutilisable que
  // cette US existe pour fermer.
  //
  // La jointure se fait par `ordre`, qui est la clé partagée entre une étape et ses instances
  // (ADR-0076 §3 : les instances d'un départ héritent de l'ordre des étapes). Aucun appel de plus
  // en pratique : `usePhases` est déjà monté par l'écran des phases et par l'assemblage, React
  // Query sert le cache partagé sur la même clé.
  const etapes = usePhases(tournoiId)
  const titreParOrdre = new Map((etapes.data ?? []).map((etape) => [etape.ordre, etape.titre]))

  return (
    <section className="carte">
      <h3 className="carte__soustitre">Piloter un créneau</h3>
      <p className="carte__aide">
        Le déroulé est commun au tournoi ; son <strong>avancement</strong> appartient à chaque
        créneau. Le départ du matin peut être en duels pendant que celui de l’après-midi qualifie.
      </p>
      {aucunCreneau && (
        <p className="carte__etat">
          Aucun départ n’est encore défini pour ce tournoi : il n’y a rien à piloter.
        </p>
      )}
      <MessageErreur erreur={phases.error} />
      {/* E05US033 — la relance des pauses, **avant** la liste des phases : quand la salle attend, c'est
          le seul geste qui compte, et le faire chercher au milieu d'une liste de six phases est
          exactement le piège du CA (« en oublier une »). */}
      {departId !== null && <RelanceDesArrets departId={departId} />}
      {departId !== null && phases.isPending && <p className="carte__etat">Chargement…</p>}
      {phases.data?.length === 0 && (
        <p className="carte__etat">
          Ce créneau ne joue encore aucune phase : composez le déroulé depuis « Phases du tournoi ».
        </p>
      )}
      {phases.data !== undefined && phases.data.length > 0 && departId !== null && (
        <ol className="liste-phases">
          {phases.data.map((phase) => (
            <LignePilotage
              key={phase.id}
              tournoiId={tournoiId}
              departId={departId}
              phase={phase}
              titre={titreParOrdre.get(phase.ordre) ?? null}
              avancement={avancementParOrdre.get(phase.ordre) ?? null}
            />
          ))}
        </ol>
      )}
    </section>
  )
}

function LignePilotage({
  tournoiId,
  departId,
  phase,
  titre,
  avancement,
}: {
  tournoiId: number
  departId: number
  phase: Phase
  /** Le libellé de l'étape correspondante — `null` si l'organisateur ne l'a pas nommée (E16US002).
   *
   * Vient de l'**étape**, pas de la phase : c'est la composition qui porte le titre. */
  titre: string | null
  /** Où en est cette phase — `null` si le suivi n'a rien à dire d'elle (E05US034). */
  avancement: AvancementBloc | null
}) {
  const changerStatut = useChangerStatutPhase(tournoiId, departId)

  return (
    <li className="phase">
      <div className="phase__ligne">
        <span className="phase__ordre">{phase.ordre}</span>
        {/* Le titre prime, le type reste lisible : c'est la lecture de l'écran des phases, portée
            ici pour que la même phase se reconnaisse des deux côtés. */}
        <span className="phase__type">{titre ?? LIBELLE_TYPE[phase.type]}</span>
        {titre !== null && <span className="phase__details">{LIBELLE_TYPE[phase.type]}</span>}
        <span className={`badge badge--${phase.statut.replace('_', '-')}`}>
          {LIBELLE_STATUT[phase.statut]}
        </span>
        <EtatDuTour avancement={avancement} />
      </div>
      <div className="phase__actions">
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
      </div>
      <PoserUnePause departId={departId} phase={phase} avancement={avancement} />
      <MessageErreur erreur={changerStatut.error} />
    </li>
  )
}

/**
 * Le tour en cours, **lisible en tant que tel** (CA E05US034).
 *
 * ⚠️ **Ce CA a été tranché ici, et la fiche demandait qu'il le soit « sur preuve d'usage ».** La
 * question ouverte était : le pilotage exige-t-il plus qu'un numéro de tour lisible — une clôture
 * **persistée** ? La réponse est non, et la preuve est ce composant : ce dont le pilotage a besoin,
 * c'est de **dire** où en est la phase, parce que le geste voisin (« bloquer dans x tours ») se
 * compte à partir de là. Persister une clôture reviendrait à écrire un second avancement à côté de
 * celui qu'ADR-0090 §5 dérive à la lecture — deux sources pour une même vérité, exactement ce que
 * cet ADR a supprimé.
 *
 * ⚠️ **La règle elle-même vit dans `shared/phases/relance.ts`** (`libelleEtatDuTour`), pas ici —
 * correctif de revue, même motif que `peutPoserUnePause` deux fonctions plus bas : écrite en
 * conditions JSX, elle était invisible au test, et son repli mort n'a été vu que par lecture. Ce
 * composant n'est plus que le point de montage.
 */
function EtatDuTour({ avancement }: { avancement: AvancementBloc | null }) {
  const libelle = libelleEtatDuTour(avancement)
  if (libelle === null) return null
  return <span className="carte__aide">{libelle}</span>
}

/**
 * « Bloquer dans x tours » — la pause décidée **pendant** que la salle tire (CA E05US034, ADR-0092).
 *
 * ⚠️ **Ce geste n'édite pas le déroulé, et c'est tout l'ADR.** Ajouter l'arrêt à l'étape du tournoi
 * l'aurait fait rejouer par le créneau du soir (ADR-0076 §4) : la panne de chauffage du matin
 * arrêterait l'après-midi. Ici on agit sur ce qui tire maintenant (§5), et rien d'autre.
 *
 * ⚠️ **Relatif et non absolu**, parce que c'est la façon dont on parle le jour J : l'organisateur
 * lit « tour 3 sur 5 » juste à gauche et pense « encore deux », pas « après le tour 4 ». La
 * conversion est faite par le **serveur** — le tour courant est une donnée serveur, et un client
 * qui le calculerait couperait au mauvais endroit dès qu'il aurait dix secondes de retard.
 *
 * **Ne s'affiche pas** sur une phase qui n'est pas en cours, sur un type dont l'application ne lit
 * pas le tour (`TYPES_ARRETABLES`), ou tant que le tour n'est pas lisible : dans les quatre cas le
 * serveur refuserait, et offrir un geste dont on sait déjà qu'il sera refusé est ce que la table de
 * transitions ci-dessus évite déjà pour le cycle de vie.
 */
function PoserUnePause({
  departId,
  phase,
  avancement,
}: {
  departId: number
  phase: Phase
  avancement: AvancementBloc | null
}) {
  const [tours, setTours] = useState('1')
  const [portee, setPortee] = useState<PorteeArret>('phase')
  const poser = usePoserArretRelatif(departId)

  // La règle vit dans `shared/phases/relance.ts`, avec ses tests : écrite ici en condition JSX,
  // elle serait invisible au test — le manque exact qui a fait naître `suisse/presentation.ts`.
  const posable = peutPoserUnePause({
    statut: phase.statut,
    type: phase.type,
    tourCourant: avancement?.tour_courant ?? null,
    nbTours: avancement?.nb_tours ?? 0,
  })
  if (!posable) return null
  // La borne vient de `toursBloquablesRestants` et non d'une soustraction écrite ici (correctif de
  // revue) : c'est elle qui est tenue en vis-à-vis du refus serveur par un test. `posable` implique
  // un tour courant lisible et strictement inférieur à `nb_tours`, donc un résultat d'au moins 1.
  const restant = toursBloquablesRestants({
    statut: phase.statut,
    type: phase.type,
    tourCourant: avancement?.tour_courant ?? null,
    nbTours: avancement?.nb_tours ?? 0,
  })

  return (
    <form
      className="phase__actions"
      onSubmit={(evenement) => {
        evenement.preventDefault()
        // Conversion **au moment du geste**, pas à la frappe : la saisie reste effaçable (voir le
        // commentaire du champ). Un champ vide ou illisible retombe sur 1 — la valeur que le
        // formulaire propose d'emblée, donc jamais une surprise.
        const demande = Number.parseInt(tours, 10)
        poser.mutate({
          phaseId: phase.id,
          dansXTours: Number.isNaN(demande) ? 1 : demande,
          portee,
        })
      }}
    >
      <label>
        Bloquer dans{' '}
        {/* ⚠️ **`max` borné par ce qui reste de la phase, pas par le plafond du DTO** (correctif de
            revue) : au-delà, le serveur refuse (« ne couperait rien »), et la même règle doit se
            lire là où l'organisateur saisit. `peutPoserUnePause` garantit ici `tourCourant !== null`
            et `tourCourant < nbTours`, donc le calcul vaut au moins 1.
            ⚠️ **La saisie est gardée en chaîne**, et convertie seulement à la soumission (correctif
            de 2ᵉ passe). Un champ contrôlé par un nombre ne peut pas être **vidé** : `Number('')`
            valait `0`, et le repli `|| 1` ne faisait que réafficher « 1 » — pire, effacer puis
            taper « 3 » produisait « 13 », donc une pause dans treize tours au lieu de trois, sur un
            geste dont le seul retour est un message transitoire (`DETTE-075`). Au doigt, en pleine
            salle, c'est ce genre de détail qui fait renoncer. */}
        <input
          type="number"
          min={1}
          max={restant}
          inputMode="numeric"
          value={tours}
          onFocus={(evenement) => evenement.target.select()}
          onChange={(evenement) => setTours(evenement.target.value)}
        />{' '}
        tour{Number.parseInt(tours, 10) > 1 ? 's' : ''}
      </label>
      <label>
        <span className="carte__aide">Portée</span>{' '}
        <select
          value={portee}
          onChange={(evenement) => setPortee(evenement.target.value as PorteeArret)}
        >
          <option value="phase">cette phase seule</option>
          <option value="depart">tout le créneau</option>
        </select>
      </label>
      <button type="submit" className="bouton--discret" disabled={poser.isPending}>
        Programmer la pause
      </button>
      {/* `# DETTE-075` — **c'est le seul retour sur une pause posée**, et il est transitoire : il
          disparaît au changement d'onglet ou au rechargement. Aucune lecture ne rend les arrêts de
          circonstance **armés** (le port a `par_depart`, mais aucune route ne l'expose). Relevé par
          quatre axes de revue ; assumé plutôt que résorbé ici, parce que la lecture est une tranche
          d'IHM à part entière et non un correctif. Cf. `docs/dette.md`. */}
      {poser.isSuccess && poser.data !== undefined && (
        <span className="carte__aide" role="status">
          Pause posée : la salle s’arrêtera après le tour {poser.data.apres_tour}.
        </span>
      )}
      <MessageErreur erreur={poser.error} />
    </form>
  )
}

/**
 * Les pauses atteintes qui attendent un geste (E05US033, ADR-0091).
 *
 * ⚠️ **Un bouton par arrêt, pas par phase**, et c'est un CA : un arrêt de portée « créneau » a pu
 * mettre quatre phases en pause, et « quatre boutons pour un seul arrêt créerait exactement le piège
 * qu'on cherche à éviter — en oublier une ». Le compte des phases concernées est donc affiché, mais
 * la commande reste unique.
 *
 * ⚠️ **Ne rend rien quand il n'y a rien à relancer**, plutôt qu'un « aucune pause en attente »
 * permanent. Le panneau de pilotage sert tous les jours ; une ligne vide qui ne bouge jamais cesse
 * d'être lue, et c'est précisément celle qu'on veut voir le jour où elle apparaît.
 */
function RelanceDesArrets({ departId }: { departId: number }) {
  const arrets = useArretsEnAttente(departId)
  const relancer = useRelancerArret(departId)
  // Battement à la minute : c'est le grain affiché (« depuis 14 min »). Sans lui, le compteur ne
  // bougerait qu'au gré des re-rendus provoqués par le poll — et resterait figé si le serveur
  // renvoyait deux fois la même réponse, ce qui est le cas normal d'une salle qui attend.
  const maintenant = useMaintenant(60000)

  if (arrets.data === undefined || arrets.data.length === 0) {
    return <MessageErreur erreur={arrets.error} />
  }
  const resume = resumeDeRelance(arrets.data, maintenant)

  return (
    <div className="carte__etat carte__etat--alerte" role="status">
      <p>
        {/* E05US034 — la phrase compte les **phases éteintes** et dit **depuis quand**, au lieu de
            compter les arrêts. Un arrêt de créneau en éteint plusieurs d'un coup : « 1 pause »
            minimisait ce qu'il y a à rallumer. Mutualisée avec la pastille du tableau de bord —
            deux formulations pour un même fait, c'est une divergence en attente.
            ⚠️ **Le repli compte, il ne suppose pas** (correctif de revue) : `resumeDeRelance` rend
            `null` quand aucun arrêt listé n'a de phase éteinte, et le singulier codé en dur
            titrait « Une pause attend » au-dessus de trois boutons de relance. Depuis que
            `en_attente_de_relance` écarte les arrêts dont plus rien n'est en pause, ce chemin ne
            devrait plus être atteint — raison de plus pour qu'il ne mente pas s'il l'était. */}
        <strong>
          {phraseDeRelance(resume ?? { nbPhases: arrets.data.length, minutes: null })}
        </strong>{' '}
        Le tir est suspendu&nbsp;: les archers concernés lisent «&nbsp;en attente&nbsp;».
      </p>
      <ul className="deroule__liste">
        {arrets.data.map((arret) => (
          <li key={arret.id}>
            <span>
              Pause après le tour {arret.apres_tour}
              {arret.portee === 'depart'
                ? ` — tout le créneau (${arret.phases_arretees.length} phase${
                    arret.phases_arretees.length > 1 ? 's' : ''
                  })`
                : ' — cette phase seule'}
            </span>
            <button
              type="button"
              className="bouton"
              disabled={relancer.isPending}
              onClick={() => relancer.mutate(arret.id)}
            >
              Relancer
            </button>
          </li>
        ))}
      </ul>
      <MessageErreur erreur={relancer.error} />
    </div>
  )
}
