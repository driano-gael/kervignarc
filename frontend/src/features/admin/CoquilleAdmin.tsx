// Coquille de navigation de l'appli admin (E00US015, refondue en E14US003).
//
// **Le découpage a changé de nature le 30/07/2026.** L'ossature groupait les destinations par
// **temps du tournoi** (Préparation / Jour J) — 19 entrées d'un côté, 6 de l'autre. Le commanditaire
// l'a refusé : « la sidebar fait vivre le tournoi sous tous ses états en même temps, je trouve cela
// confus ». Le critère n'est plus *quand*, c'est **quelle activité** — trois axes :
//
//  - **atelier** — fabriquer, **hors tournoi** : briques du club, salles types, formats, banc d'essai ;
//  - **pilotage** — le temps réel : lancer, superviser, valider, faire tourner la journée ;
//  - **gestion** — l'administratif, **transverse au temps** : inscriptions, paiements, exports.
//
// Pourquoi ce n'est pas un renommage : un rangement **temporel coupe en morceaux** une activité qui
// dure. La gestion administrative en était la preuve — inscriptions, doublons et paiements étaient
// rangés dans « Préparation », exports et archive dans « Jour J ». Personne ne l'avait décidé : c'était
// l'ordre d'arrivée des US, une entrée de sidebar par US livrée.
//
// Conséquences de structure :
//  - **un accueil admin choisit l'axe** (`axeActif === null`), et porte l'**assemblage** — la liste
//    des tournois, leur création, leur cycle de vie. Un seul axe est ouvert à la fois : les groupes
//    repliables disparaissent, la sidebar ne montre que les destinations de l'axe courant. `P-3` est
//    respecté — l'accueil est à un clic, rien n'est interdit — mais on n'est plus *pollué* par les
//    deux autres axes.
//  - **le sélecteur de tournoi ne coiffe plus tout** : l'atelier n'a **pas** de tournoi (patrimoine du
//    club), donc le sélecteur n'apparaît que dans les axes qui en ont besoin. L'exception « ici le
//    sélecteur ne s'applique pas » disparaît au lieu d'être expliquée.
//  - l'**accueil-tableau de bord** (E14US001) et le **cockpit de simulation** (E15US003) cessent
//    d'être des destinations parmi dix-neuf : le premier est la destination d'ouverture du pilotage
//    (`D-20`), le second l'entrée du banc d'essai de l'atelier.
//
// **Chaque écran a son adresse** : `/admin` ouvre l'accueil des axes, `/admin/pilotage/supervision`
// ouvre un écran précis. L'axe et la destination ne sont donc **pas** dupliqués en état local — c'est
// ce qui fait qu'un `F5` revient là où l'on était et qu'un lien se partage. Routeur **maison**
// (`app/routeur.ts`), pas de dépendance : cf. son en-tête pour le pourquoi.
//
// Périmètre borné aux **fonctions livrées** (CA « non-régression ») : les destinations que le CDC UX
// prévoit mais qui n'existent pas encore (Identité, Validation, Podiums, Audit) ne sont **pas**
// matérialisées par des entrées vides — elles arriveront avec leur US. La **recherche d'archer**
// (E12US006, `D-19`) reste hors du système de destinations : elle coiffe la sidebar, elle ne s'ouvre
// pas dans la zone principale. Elle est scopée au tournoi courant, donc n'apparaît que dans les axes
// qui en ont un — sa variante « toutes entités » pour l'atelier relève du lot suivant.
//
// **DETTE-023 — l'atelier montre encore des briques scopées par tournoi.** Catégories, Blasons,
// Barème et Phases sont rangés dans l'atelier (c'est leur place : patrimoine du club) mais leurs
// endpoints portent encore un `tournoi_id` (`/tournois/{id}/categories`, `/tournois/{id}/blasons`…) :
// ils exigent donc un tournoi courant, ce qui contredit la promesse de l'axe. Le découpage est livré
// **avant** la libération des briques, volontairement — voir le registre de dette.

import { useState, type ReactNode } from 'react'
import { Accueil } from '../accueil/Accueil'
import { Archers } from '../archers/Archers'
import { Archive } from '../archive/Archive'
import { Doublons } from '../archers/Doublons'
import { NouvelArcher } from '../archers/NouvelArcher'
import { BaremeQualification } from '../bareme/BaremeQualification'
import { Blasons } from '../blasons/Blasons'
import { Categories } from '../categories/Categories'
import { Clubs } from '../clubs/Clubs'
import { Completude } from '../completude/Completude'
import type { Tournoi } from '../competition/api'
import { useTournois } from '../competition/hooks'
import { VueClassement } from '../competition/VueClassement'
import { Departs } from '../departs/Departs'
import { Duels } from '../duels/Duels'
import { Exports } from '../exports/Exports'
import { Gabarits } from '../gabarits/Gabarits'
import { PlanDeSalle } from '../gabarits/PlanDeSalle'
import { GrainValidation } from '../grain-validation/GrainValidation'
import { JeuEssai } from '../jeu-essai/JeuEssai'
import { Paiements } from '../paiements/Paiements'
import { Phases } from '../phases/Phases'
import { Placement } from '../placement/Placement'
import { Postes } from '../postes/Postes'
import { Scoreurs } from '../scoreurs/Scoreurs'
import { FeuVert } from '../feu-vert/FeuVert'
import { Simulation } from '../simulation/Simulation'
import { Supervision } from '../supervision/Supervision'
import { RechercheArcher } from '../recherche/RechercheArcher'
import { useSessionAdminStore } from '../../shared/stores/sessionAdminStore'
import { AideEcran } from '../../shared/ui/AideEcran'
import { ConnexionAdmin } from './ConnexionAdmin'
import { AIDE_ECRANS, type DestinationAdminId } from './aide-ecrans'
import {
  AXES,
  axeDepuisSegments,
  destinationDepuisSegments,
  destinationParDefaut,
  type Axe,
} from './axes'
import { analyserChemin, construireChemin } from '../../app/routeur'
import { naviguer, useChemin } from '../../app/useChemin'
import { BadgeStatut } from '../competition/BadgeStatut'
import { GestionTournois } from '../tournois/Tournois'

// L'appli admin (coquille) n'est présentée qu'à un admin connecté. Elle n'est atteinte que par la
// **porte Admin** de l'écran d'accueil (E00US017, ADR-0042) : sans session, on affiche donc le
// **login** (E10US002) — plus la consultation publique, désormais sa propre porte. La lecture
// publique passe par la porte « Téléphone », le scoreur et la tablette par les leurs.
export function CoquilleAdmin() {
  const estAdmin = useSessionAdminStore((s) => s.jeton) !== null
  if (estAdmin) return <Coquille />
  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">Administration</h2>
      <ConnexionAdmin />
    </section>
  )
}

// ————————————————————————————————————————————————————————————————————————————————————————————————
// Coquille admin : accueil des trois axes, puis sidebar de l'axe courant + zone principale.
// ————————————————————————————————————————————————————————————————————————————————————————————————

function Coquille() {
  const tournois = useTournois()
  const [tournoiId, setTournoiId] = useState<number | null>(null)
  // **L'axe et la destination vivent dans l'adresse** (E14US003) : `/admin` = l'accueil qui choisit
  // l'axe, `/admin/pilotage/supervision` = un écran précis. Rien n'est dupliqué en état local — c'est
  // ce qui fait qu'un `F5` revient exactement où l'on était, et qu'un lien se partage.
  const segments = analyserChemin(useChemin()).segments
  const axeActif = axeDepuisSegments(segments)

  // Version **fraîche** du tournoi courant : après un démarrer/terminer, la liste est invalidée et
  // re-lue, ce qui rafraîchit le statut ici (badge, accueil) sans état local à synchroniser.
  const courant =
    tournoiId === null ? null : (tournois.data?.find((t) => t.id === tournoiId) ?? null)

  const allerA = (axe: Axe, destination: DestinationAdminId) =>
    naviguer(construireChemin({ monde: 'admin', segments: [axe, destination] }))

  const entrerDansAxe = (axe: Axe) => allerA(axe, destinationParDefaut(axe))

  // Choisir un tournoi **depuis l'accueil** le rend courant et ouvre son **pilotage** sur l'accueil
  // contextualisé (`D-20`) : c'est le geste « je viens m'occuper de ce tournoi ».
  const entrerDansTournoi = (t: Tournoi) => {
    setTournoiId(t.id)
    entrerDansAxe('pilotage')
  }

  // Changer de tournoi **depuis le sélecteur**, à l'intérieur d'un axe : on reste où l'on travaille.
  // Ne pas arracher l'admin de son écran est le pendant de `P-3` — la priorité d'affichage guide,
  // elle ne contraint pas. Le badge de statut, lui, se met à jour en direct.
  const changerTournoi = (t: Tournoi) => setTournoiId(t.id)

  // Chaque destination = une **feature autonome** montée par **une seule entrée** (guide §8). Les
  // destinations `besoinTournoi` exigent un tournoi courant ; les autres (Gabarits, Clubs) sont des
  // référentiels **globaux**, hors tournoi. Défini dans le composant pour fermer sur `courant` /
  // `choisirTournoi` ; `rendu` n'est appelé que lorsque le garde `besoinTournoi` est satisfait.
  const destinations: {
    // Typé par l'union des `id` d'aide (et non `string`) : ajouter une destination sans son entrée
    // dans `AIDE_ECRANS` ne compile plus — la couverture « une aide par écran » (E14US002) est
    // garantie par `tsc`, plus par une vérification manuelle.
    id: DestinationAdminId
    libelle: string
    axe: Axe
    besoinTournoi: boolean
    rendu: () => ReactNode
  }[] = [
    {
      id: 'accueil',
      libelle: 'Accueil (tableau de bord)',
      axe: 'pilotage',
      // Accueil-tableau de bord contextualisé (E14US001, `D-20`) : la « photo d'ensemble » du tournoi
      // courant (frise, checklist, chiffres). Destination d'ouverture par défaut (`destinationParDefaut`).
      besoinTournoi: true,
      rendu: () => courant && <Accueil tournoi={courant} />,
    },
    {
      id: 'categories',
      libelle: 'Catégories',
      axe: 'atelier',
      besoinTournoi: true,
      rendu: () => courant && <Categories tournoiId={courant.id} />,
    },
    {
      id: 'blasons',
      libelle: 'Blasons',
      axe: 'atelier',
      besoinTournoi: true,
      rendu: () => courant && <Blasons tournoiId={courant.id} />,
    },
    {
      id: 'gabarits',
      libelle: 'Gabarits (modèles)',
      axe: 'atelier',
      besoinTournoi: false,
      rendu: () => <Gabarits />,
    },
    {
      id: 'plan',
      libelle: 'Plan de salle',
      axe: 'pilotage',
      besoinTournoi: true,
      rendu: () => courant && <PlanDeSalle tournoiId={courant.id} />,
    },
    {
      id: 'bareme',
      libelle: 'Barème & validation',
      axe: 'atelier',
      besoinTournoi: true,
      // Le grain de validation se règle sur la même phase que le barème et n'a de sens qu'une fois
      // celui-ci défini (E01US015) : les deux vont ensemble sur une même destination.
      rendu: () =>
        courant && (
          <>
            <BaremeQualification tournoiId={courant.id} />
            <GrainValidation tournoiId={courant.id} />
          </>
        ),
    },
    {
      id: 'phases',
      libelle: 'Phases (format)',
      axe: 'atelier',
      besoinTournoi: true,
      // Séquence des phases du moteur (E05US001, ADR-0045) : élimination directe / placement après
      // la qualification. Juste après « Barème & validation » — c'est la suite de la définition du
      // format (la qualification, elle, se règle sur cet écran-là).
      rendu: () => courant && <Phases tournoiId={courant.id} />,
    },
    {
      id: 'departs',
      libelle: 'Départs & tarifs',
      axe: 'pilotage',
      besoinTournoi: true,
      // Les départs (créneaux) portent le tarif (E02US004, ADR-0017).
      rendu: () => courant && <Departs tournoiId={courant.id} />,
    },
    {
      id: 'clubs',
      libelle: 'Clubs',
      axe: 'atelier',
      besoinTournoi: false,
      rendu: () => <Clubs />,
    },
    {
      id: 'scoreurs',
      libelle: 'Scoreurs',
      axe: 'pilotage',
      besoinTournoi: true,
      rendu: () => courant && <Scoreurs tournoiId={courant.id} />,
    },
    {
      id: 'inscriptions',
      libelle: 'Inscriptions',
      axe: 'gestion',
      besoinTournoi: true,
      // Créer un archer, puis le corriger / l'inscrire sur des départs : les deux briques de la
      // feature « archers » (création + liste) sur une même destination.
      rendu: () =>
        courant && (
          <>
            <NouvelArcher tournoiId={courant.id} />
            <Archers tournoiId={courant.id} />
          </>
        ),
    },
    {
      id: 'doublons',
      libelle: 'Doublons',
      axe: 'gestion',
      // Nettoyage de la liste des inscrits (E02US005) : repérer les fiches en double et fusionner.
      // Juste après « Inscriptions » — c'est la suite naturelle du travail sur la liste.
      besoinTournoi: true,
      rendu: () => courant && <Doublons tournoiId={courant.id} />,
    },
    {
      id: 'placement',
      libelle: 'Placement',
      axe: 'pilotage',
      besoinTournoi: true,
      rendu: () => courant && <Placement tournoiId={courant.id} />,
    },
    {
      id: 'duels',
      libelle: 'Plan de duels',
      axe: 'pilotage',
      besoinTournoi: true,
      // Ajustement du placement des duellistes d'une phase de tableau (E03US009, ADR-0048). L'écran
      // choisit lui-même la **phase** (comme « Placement » choisit le départ) : la navigation reste
      // par `useState` local, sans react-router (arbitrage du 18/07/2026 — cf. en-tête de fichier).
      rendu: () => courant && <Duels tournoiId={courant.id} />,
    },
    {
      id: 'paiements',
      libelle: 'Paiements',
      axe: 'gestion',
      besoinTournoi: true,
      rendu: () => courant && <Paiements tournoiId={courant.id} />,
    },
    {
      id: 'postes',
      libelle: 'Postes de cible',
      axe: 'pilotage',
      besoinTournoi: true,
      rendu: () => courant && <Postes tournoiId={courant.id} />,
    },
    {
      id: 'jeu-essai',
      libelle: 'Jeu d’essai',
      axe: 'atelier',
      // Outil de démo/QA (E15US001) : peupler le tournoi courant OU instancier un scénario qui crée
      // son propre tournoi — d'où `besoinTournoi: false` (la brique « peupler » gère elle-même
      // l'absence de tournoi courant). À l'instanciation, on **sort de l'atelier** pour aller piloter
      // le tournoi qui vient de naître : c'est le geste « j'ai fabriqué, je vais m'en servir ».
      besoinTournoi: false,
      rendu: () => (
        <JeuEssai
          tournoiId={tournoiId}
          onTournoiInstancie={(id) => {
            setTournoiId(id)
            entrerDansAxe('pilotage')
          }}
        />
      ),
    },
    {
      id: 'simulation',
      libelle: 'Simulation',
      axe: 'atelier',
      // Cockpit de simulation (E15US003) : rejoue le tournoi courant en accéléré **sans rien
      // enregistrer** (bot pausable + reprise en main + vues cible/archer/scoreur/public). Ne simule
      // qu'un tournoi avant démarrage (garde-fou serveur) — d'où sa place dans « Préparation ».
      besoinTournoi: true,
      rendu: () => courant && <Simulation tournoiId={courant.id} />,
    },
    {
      id: 'supervision',
      libelle: 'Supervision',
      axe: 'pilotage',
      besoinTournoi: true,
      rendu: () => courant && <Supervision tournoiId={courant.id} />,
    },
    {
      // Feu vert / lancer le tour (E12US002) : le geste central du jour J — voir en continu ce qui
      // est prêt à partir, puis faire partir les duels prêts (les postes/écrans sont prévenus).
      id: 'feu-vert',
      libelle: 'Feu vert',
      axe: 'pilotage',
      besoinTournoi: true,
      rendu: () => courant && <FeuVert tournoiId={courant.id} />,
    },
    {
      id: 'completude',
      libelle: 'Complétude',
      axe: 'pilotage',
      besoinTournoi: true,
      // « Qu'est-ce qui manque pour finir ? » (E12US005) + contrôle avant de terminer. Le statut
      // pilote l'apparition du bouton « Terminer » (uniquement *en cours*).
      rendu: () => courant && <Completude tournoiId={courant.id} statut={courant.statut} />,
    },
    {
      id: 'classement',
      libelle: 'Classement en direct',
      axe: 'pilotage',
      besoinTournoi: true,
      rendu: () => courant && <VueClassement tournoiId={courant.id} admin />,
    },
    {
      id: 'exports',
      libelle: 'Exports',
      axe: 'gestion',
      // Listes imprimables du jour J (E09US003) : placement (accueil) et club & paiement (admin).
      // Destination prévue au §7.1, désormais matérialisée sur le socle PDF (E09US001).
      besoinTournoi: true,
      rendu: () => courant && <Exports tournoiId={courant.id} />,
    },
    {
      id: 'archive',
      libelle: 'Archive',
      axe: 'gestion',
      // Paquet ZIP de fin de tournoi (E11US003) : instantané SQLite + CSV + PDF régénérés + manifeste,
      // au choix (cases à cocher). Destination prévue au §7.1, désormais matérialisée.
      besoinTournoi: true,
      rendu: () => courant && <Archive tournoiId={courant.id} />,
    },
  ]

  // Accueil de l'admin : aucun axe ouvert. Il porte le choix de l'axe **et** l'assemblage (la liste
  // des tournois, leur création, leur cycle de vie) — l'ancienne destination « Tournoi », qui
  // n'appartenait à aucun des trois axes puisqu'elle *crée* l'objet sur lequel deux d'entre eux
  // travaillent.
  if (axeActif === null) {
    const enCours = (tournois.data ?? []).filter(
      (t) => t.statut === 'en_cours' || t.statut === 'en_pause',
    ).length
    return (
      <div className="accueil-admin">
        <ul className="accueil-admin__axes">
          {AXES.map((a) => (
            <li key={a.axe}>
              <button
                type="button"
                className="accueil-admin__axe"
                onClick={() => entrerDansAxe(a.axe)}
              >
                <span className="accueil-admin__titre">
                  {a.libelle}
                  {a.axe === 'atelier' && (
                    <span className="accueil-admin__marque">sans tournoi</span>
                  )}
                  {a.axe === 'pilotage' && enCours > 0 && (
                    <span className="accueil-admin__marque accueil-admin__marque--vif">
                      {enCours} en cours
                    </span>
                  )}
                </span>
                <span className="accueil-admin__phrase">{a.phrase}</span>
              </button>
            </li>
          ))}
        </ul>
        {/* L'aide de l'écran « Tournoi » suit l'écran (E14US002) : il change de place, sa couverture
            d'aide ne doit pas disparaître pour autant. */}
        <AideEcran texte={AIDE_ECRANS['tournoi']} />
        <GestionTournois selectionneId={tournoiId} onChoisi={entrerDansTournoi} />
      </div>
    )
  }

  const axe = AXES.find((a) => a.axe === axeActif)!
  const dansAxe = destinations.filter((d) => d.axe === axeActif)
  // La destination vient de l'adresse, **validée contre les destinations de cet axe** : sans ça,
  // `/admin/atelier/supervision` afficherait un écran de pilotage sous l'intitulé « Atelier ».
  // À défaut, l'ouverture de l'axe. `dansAxe` n'est jamais vide (chaque axe a au moins une
  // destination) : le repli lève le `T | undefined` de l'accès indexé (`noUncheckedIndexedAccess`).
  const demandee = destinationDepuisSegments(
    segments,
    dansAxe.map((d) => d.id),
  )
  const active = dansAxe.find((d) => d.id === demandee) ?? dansAxe[0]!
  const contenu =
    active.besoinTournoi && courant === null ? (
      <p className="carte__etat">
        Choisissez un tournoi ci-dessus pour accéder à «&nbsp;{active.libelle}&nbsp;».
      </p>
    ) : (
      active.rendu()
    )

  return (
    <div className="coquille">
      <nav className="coquille__nav" aria-label="Navigation d'administration">
        {/* Retour à l'accueil : l'axe se quitte par un geste explicite. `P-3` est tenu — c'est un
            clic — mais on ne travaille jamais dans deux axes à la fois. */}
        <button
          type="button"
          className="coquille__retour"
          onClick={() => naviguer(construireChemin({ monde: 'admin', segments: [] }))}
        >
          ← Accueil
        </button>
        <p className="coquille__axe">{axe.libelle}</p>

        {/* La recherche d'archer coiffe la sidebar (E12US006, `D-19`) : elle répond à « je tire où ? »
            sans quitter l'écran courant. Scopée au tournoi courant, elle n'a donc rien à faire dans
            l'atelier, qui n'en a pas. */}
        {axe.besoinTournoi && <RechercheArcher tournoiId={tournoiId} />}

        {/* Le sélecteur de tournoi ne coiffe que les axes qui travaillent **sur** un tournoi. */}
        {axe.besoinTournoi && (
          <div className="coquille__selecteur">
            <label className="formulaire__libelle" htmlFor="coquille-tournoi">
              Tournoi
            </label>
            <select
              id="coquille-tournoi"
              className="formulaire__champ"
              value={tournoiId ?? ''}
              onChange={(e) => {
                const id = Number(e.target.value)
                const t = tournois.data?.find((x) => x.id === id)
                if (t) changerTournoi(t)
              }}
            >
              <option value="">— Choisir un tournoi —</option>
              {(tournois.data ?? []).map((t) => (
                <option key={t.id} value={t.id}>
                  {t.nom} — {t.date}
                </option>
              ))}
            </select>
            {courant && <BadgeStatut statut={courant.statut} />}
          </div>
        )}

        {/* Un seul axe est ouvert : la liste est **plate**. Les en-têtes de groupe repliables n'ont
            plus de raison d'être — c'est leur coexistence qui rendait la sidebar confuse. */}
        <ul className="coquille__liens">
          {dansAxe.map((d) => (
            <li key={d.id}>
              <button
                type="button"
                className={
                  d.id === active.id ? 'coquille__lien coquille__lien--actif' : 'coquille__lien'
                }
                aria-current={d.id === active.id ? 'page' : undefined}
                onClick={() => allerA(axeActif, d.id)}
              >
                {d.libelle}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div className="coquille__contenu">
        {/* Aide contextuelle de la destination active (E14US002). Rendue **ici**, au niveau de la
            coquille, plutôt que dans chacune des 22 features : la coquille connaît déjà la destination
            active, un seul point d'insertion couvre donc tous les écrans (`AIDE_ECRANS` fournit le
            texte par `id`). Au-dessus du contenu — y compris de l'invite « choisissez un tournoi »,
            où expliquer l'écran est encore plus utile. `key={active.id}` **remonte une instance neuve
            à chaque changement d'écran** : sans lui, l'état `ouvert` (local) survivrait à la
            navigation et la nouvelle aide s'afficherait déjà dépliée — or le CA la veut **repliée par
            défaut** sur chaque écran. */}
        <AideEcran key={active.id} texte={AIDE_ECRANS[active.id]} />
        {contenu}
      </div>
    </div>
  )
}
