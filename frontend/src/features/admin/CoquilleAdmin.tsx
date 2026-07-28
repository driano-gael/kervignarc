// Coquille de navigation de l'appli admin (E00US015) — ossature du CDC UX §7.1 (`D-19`, `D-20`).
//
// Remplace l'écran monolithique `competition/TrancheVerticale.tsx`, qui empilait ~14 sections dans
// une seule carte, sans navigation. Désormais :
//  - une **sidebar** groupe les destinations par **temps du tournoi** (Préparation / Jour J) et
//    n'affiche **qu'une** destination à la fois dans la zone principale ; toutes restent accessibles
//    en permanence (`P-3`, replié ≠ interdit) ;
//  - le **sélecteur de tournoi coiffe** la navigation — tout ce qui est en dessous lui appartient
//    (évite la faute classique : modifier le mauvais tournoi) ;
//  - l'**accueil est contextualisé** par le statut du tournoi (`D-20`) : c'est une **priorité
//    d'affichage, pas une restriction** — les autres destinations restent à un clic.
//
// Navigation par **état local `useState`** (pas de `react-router`) — arbitrage du 18/07/2026 : le
// périmètre (réseau local, pas de deep-link ni d'URL partagée) ne justifie pas la dépendance
// (règle 11) ; à réévaluer si un vrai besoin d'URL apparaît.
//
// Périmètre borné aux **fonctions livrées** (CA « non-régression ») : les destinations que le §7.1
// prévoit mais qui n'existent pas encore (Identité, Validation, Podiums, Audit)
// ne sont **pas** matérialisées par des entrées vides — elles arriveront avec leur US. « Exports »
// (E09US003) et « Archive » (E11US003) sont désormais livrées, dans le groupe Jour J. La
// **recherche d'archer** (E12US006, `D-19`) est désormais livrée : champ permanent en tête de la
// sidebar, hors du système de destinations (elle coiffe, elle ne s'ouvre pas dans la zone principale).
// « Complétude » (E12US005) est désormais livrée, dans le groupe Jour J. L'**accueil contextualisé**
// est désormais un **écran** à part entière (E14US001, `Accueil`) : frise du cycle de vie 7 statuts
// (ADR-0026, front aligné en E14US001) + checklist « à faire » (complétude) + chiffres-clés & alertes
// (supervision, paiements). Choisir un tournoi ouvre sur son accueil, quel que soit son statut — la
// contextualisation se joue **dans** l'écran, plus dans le choix de la destination d'ouverture.

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
// Coquille admin : sélecteur de tournoi + sidebar groupée par temps + zone principale.
// ————————————————————————————————————————————————————————————————————————————————————————————————

type Temps = 'preparation' | 'jourj'

const GROUPES: { temps: Temps; libelle: string }[] = [
  { temps: 'preparation', libelle: 'Préparation' },
  { temps: 'jourj', libelle: 'Jour J' },
]

// Destination d'ouverture quand on choisit un tournoi (`D-20`) : **toujours** l'accueil-tableau de
// bord (E14US001). C'est lui qui se contextualise par statut (frise, checklist, chiffres) — inutile
// donc d'aiguiller vers des écrans différents selon le statut. Les autres destinations restent à un
// clic (`P-3`, priorité d'affichage, pas restriction).
function destinationParDefaut(): { id: string; groupe: Temps } {
  return { id: 'accueil', groupe: 'preparation' }
}

function Coquille() {
  const tournois = useTournois()
  const [tournoiId, setTournoiId] = useState<number | null>(null)
  const [destinationActive, setDestinationActive] = useState<string>('tournoi')
  const [groupeOuvert, setGroupeOuvert] = useState<Temps>('preparation')

  // Version **fraîche** du tournoi courant : après un démarrer/terminer, la liste est invalidée et
  // re-lue, ce qui rafraîchit le statut ici (badge, accueil) sans état local à synchroniser.
  const courant =
    tournoiId === null ? null : (tournois.data?.find((t) => t.id === tournoiId) ?? null)

  // Choisir un tournoi le rend courant **et** saute à son accueil contextualisé (`D-20`). On ne le
  // fait qu'au **changement de tournoi**, pas à chaque changement de statut : démarrer un tournoi
  // ne doit pas arracher l'admin de l'écran où il travaille (la priorité d'affichage guide, elle ne
  // contraint pas — `P-3`). Le badge, lui, se met à jour en direct.
  const choisirTournoi = (t: Tournoi) => {
    setTournoiId(t.id)
    const defaut = destinationParDefaut()
    setDestinationActive(defaut.id)
    setGroupeOuvert(defaut.groupe)
  }

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
    groupe: Temps
    besoinTournoi: boolean
    rendu: () => ReactNode
  }[] = [
    {
      id: 'tournoi',
      libelle: 'Tournoi',
      groupe: 'preparation',
      besoinTournoi: false,
      rendu: () => <GestionTournois selectionneId={tournoiId} onChoisi={choisirTournoi} />,
    },
    {
      id: 'accueil',
      libelle: 'Accueil (tableau de bord)',
      groupe: 'preparation',
      // Accueil-tableau de bord contextualisé (E14US001, `D-20`) : la « photo d'ensemble » du tournoi
      // courant (frise, checklist, chiffres). Destination d'ouverture par défaut (`destinationParDefaut`).
      besoinTournoi: true,
      rendu: () => courant && <Accueil tournoi={courant} />,
    },
    {
      id: 'categories',
      libelle: 'Catégories',
      groupe: 'preparation',
      besoinTournoi: true,
      rendu: () => courant && <Categories tournoiId={courant.id} />,
    },
    {
      id: 'blasons',
      libelle: 'Blasons',
      groupe: 'preparation',
      besoinTournoi: true,
      rendu: () => courant && <Blasons tournoiId={courant.id} />,
    },
    {
      id: 'gabarits',
      libelle: 'Gabarits (modèles)',
      groupe: 'preparation',
      besoinTournoi: false,
      rendu: () => <Gabarits />,
    },
    {
      id: 'plan',
      libelle: 'Plan de salle',
      groupe: 'preparation',
      besoinTournoi: true,
      rendu: () => courant && <PlanDeSalle tournoiId={courant.id} />,
    },
    {
      id: 'bareme',
      libelle: 'Barème & validation',
      groupe: 'preparation',
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
      groupe: 'preparation',
      besoinTournoi: true,
      // Séquence des phases du moteur (E05US001, ADR-0045) : élimination directe / placement après
      // la qualification. Juste après « Barème & validation » — c'est la suite de la définition du
      // format (la qualification, elle, se règle sur cet écran-là).
      rendu: () => courant && <Phases tournoiId={courant.id} />,
    },
    {
      id: 'departs',
      libelle: 'Départs & tarifs',
      groupe: 'preparation',
      besoinTournoi: true,
      // Les départs (créneaux) portent le tarif (E02US004, ADR-0017).
      rendu: () => courant && <Departs tournoiId={courant.id} />,
    },
    {
      id: 'clubs',
      libelle: 'Clubs',
      groupe: 'preparation',
      besoinTournoi: false,
      rendu: () => <Clubs />,
    },
    {
      id: 'scoreurs',
      libelle: 'Scoreurs',
      groupe: 'preparation',
      besoinTournoi: true,
      rendu: () => courant && <Scoreurs tournoiId={courant.id} />,
    },
    {
      id: 'inscriptions',
      libelle: 'Inscriptions',
      groupe: 'preparation',
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
      groupe: 'preparation',
      // Nettoyage de la liste des inscrits (E02US005) : repérer les fiches en double et fusionner.
      // Juste après « Inscriptions » — c'est la suite naturelle du travail sur la liste.
      besoinTournoi: true,
      rendu: () => courant && <Doublons tournoiId={courant.id} />,
    },
    {
      id: 'placement',
      libelle: 'Placement',
      groupe: 'preparation',
      besoinTournoi: true,
      rendu: () => courant && <Placement tournoiId={courant.id} />,
    },
    {
      id: 'duels',
      libelle: 'Plan de duels',
      groupe: 'preparation',
      besoinTournoi: true,
      // Ajustement du placement des duellistes d'une phase de tableau (E03US009, ADR-0048). L'écran
      // choisit lui-même la **phase** (comme « Placement » choisit le départ) : la navigation reste
      // par `useState` local, sans react-router (arbitrage du 18/07/2026 — cf. en-tête de fichier).
      rendu: () => courant && <Duels tournoiId={courant.id} />,
    },
    {
      id: 'paiements',
      libelle: 'Paiements',
      groupe: 'preparation',
      besoinTournoi: true,
      rendu: () => courant && <Paiements tournoiId={courant.id} />,
    },
    {
      id: 'postes',
      libelle: 'Postes de cible',
      groupe: 'preparation',
      besoinTournoi: true,
      rendu: () => courant && <Postes tournoiId={courant.id} />,
    },
    {
      id: 'jeu-essai',
      libelle: 'Jeu d’essai',
      groupe: 'preparation',
      // Outil de démo/QA (E15US001) : peupler le tournoi courant OU instancier un scénario qui crée
      // son propre tournoi — d'où `besoinTournoi: false` (la brique « peupler » gère elle-même
      // l'absence de tournoi courant). À l'instanciation, on bascule sur le tournoi créé et son accueil.
      besoinTournoi: false,
      rendu: () => (
        <JeuEssai
          tournoiId={tournoiId}
          onTournoiInstancie={(id) => {
            setTournoiId(id)
            setDestinationActive('accueil')
            setGroupeOuvert('preparation')
          }}
        />
      ),
    },
    {
      id: 'simulation',
      libelle: 'Simulation',
      groupe: 'preparation',
      // Cockpit de simulation (E15US003) : rejoue le tournoi courant en accéléré **sans rien
      // enregistrer** (bot pausable + reprise en main + vues cible/archer/scoreur/public). Ne simule
      // qu'un tournoi avant démarrage (garde-fou serveur) — d'où sa place dans « Préparation ».
      besoinTournoi: true,
      rendu: () => courant && <Simulation tournoiId={courant.id} />,
    },
    {
      id: 'supervision',
      libelle: 'Supervision',
      groupe: 'jourj',
      besoinTournoi: true,
      rendu: () => courant && <Supervision tournoiId={courant.id} />,
    },
    {
      // Feu vert / lancer le tour (E12US002) : le geste central du jour J — voir en continu ce qui
      // est prêt à partir, puis faire partir les duels prêts (les postes/écrans sont prévenus).
      id: 'feu-vert',
      libelle: 'Feu vert',
      groupe: 'jourj',
      besoinTournoi: true,
      rendu: () => courant && <FeuVert tournoiId={courant.id} />,
    },
    {
      id: 'completude',
      libelle: 'Complétude',
      groupe: 'jourj',
      besoinTournoi: true,
      // « Qu'est-ce qui manque pour finir ? » (E12US005) + contrôle avant de terminer. Le statut
      // pilote l'apparition du bouton « Terminer » (uniquement *en cours*).
      rendu: () => courant && <Completude tournoiId={courant.id} statut={courant.statut} />,
    },
    {
      id: 'classement',
      libelle: 'Classement en direct',
      groupe: 'jourj',
      besoinTournoi: true,
      rendu: () => courant && <VueClassement tournoiId={courant.id} admin />,
    },
    {
      id: 'exports',
      libelle: 'Exports',
      groupe: 'jourj',
      // Listes imprimables du jour J (E09US003) : placement (accueil) et club & paiement (admin).
      // Destination prévue au §7.1, désormais matérialisée sur le socle PDF (E09US001).
      besoinTournoi: true,
      rendu: () => courant && <Exports tournoiId={courant.id} />,
    },
    {
      id: 'archive',
      libelle: 'Archive',
      groupe: 'jourj',
      // Paquet ZIP de fin de tournoi (E11US003) : instantané SQLite + CSV + PDF régénérés + manifeste,
      // au choix (cases à cocher). Destination prévue au §7.1, désormais matérialisée.
      besoinTournoi: true,
      rendu: () => courant && <Archive tournoiId={courant.id} />,
    },
  ]

  // `destinations` est une liste littérale non vide (sa 1ʳᵉ entrée est « Tournoi ») : le repli est
  // toujours défini. L'assertion lève le `T | undefined` de l'accès indexé (noUncheckedIndexedAccess).
  const active = destinations.find((d) => d.id === destinationActive) ?? destinations[0]!
  const contenu =
    active.besoinTournoi && courant === null ? (
      <p className="carte__etat">
        Sélectionnez ou créez un tournoi (destination « Tournoi ») pour accéder à «&nbsp;
        {active.libelle}&nbsp;».
      </p>
    ) : (
      active.rendu()
    )

  return (
    <div className="coquille">
      <nav className="coquille__nav" aria-label="Navigation d'administration">
        {/* La recherche d'archer coiffe la sidebar (E12US006, `D-19`) : présente en permanence, quel
            que soit l'écran, elle répond à « je tire où ? » sans quitter la page courante. Scopée au
            tournoi courant, elle reste inerte tant qu'aucun n'est choisi. */}
        <RechercheArcher tournoiId={tournoiId} />

        {/* Le sélecteur de tournoi est **au-dessus de tout** : tout ce qui suit lui appartient. */}
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
              if (t) choisirTournoi(t)
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

        {GROUPES.map((groupe) => {
          const ouvert = groupeOuvert === groupe.temps
          return (
            <div className="coquille__groupe" key={groupe.temps}>
              <button
                type="button"
                className="coquille__entete-groupe"
                aria-expanded={ouvert}
                onClick={() => setGroupeOuvert(groupe.temps)}
              >
                {groupe.libelle}
              </button>
              {ouvert && (
                <ul className="coquille__liens">
                  {destinations
                    .filter((d) => d.groupe === groupe.temps)
                    .map((d) => (
                      <li key={d.id}>
                        <button
                          type="button"
                          className={
                            d.id === active.id
                              ? 'coquille__lien coquille__lien--actif'
                              : 'coquille__lien'
                          }
                          aria-current={d.id === active.id ? 'page' : undefined}
                          onClick={() => setDestinationActive(d.id)}
                        >
                          {d.libelle}
                        </button>
                      </li>
                    ))}
                </ul>
              )}
            </div>
          )
        })}
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
