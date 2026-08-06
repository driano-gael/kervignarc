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
// **Chaque écran a son adresse** : `/admin` ouvre l'accueil des axes, `/admin/12/pilotage/supervision`
// ouvre un écran précis **sur un tournoi précis**. Le tournoi, l'axe et la destination ne sont donc
// **pas** dupliqués en état local — c'est ce qui fait qu'un `F5` revient là où l'on était et qu'un lien
// s'ouvre sur la même vue. Routeur **maison** (`shared/navigation/routeur.ts`), pas de dépendance :
// cf. son en-tête pour le pourquoi (ADR-0059).
//
// Périmètre borné aux **fonctions livrées** (CA « non-régression ») : les destinations que le CDC UX
// prévoit mais qui n'existent pas encore (Identité, Validation, Podiums, Audit) ne sont **pas**
// matérialisées par des entrées vides — elles arriveront avec leur US. La **recherche d'archer**
// (E12US006, `D-19`) reste hors du système de destinations : elle coiffe la sidebar, elle ne s'ouvre
// pas dans la zone principale. Elle est scopée au tournoi courant, donc n'apparaît que dans les axes
// qui en ont un — sa variante « toutes entités » pour l'atelier relève du lot suivant.
//
// **E01US023 a rendu l'atelier honnête** (DETTE-023 résorbée, ADR-0060). Catégories, Blasons et
// Formats y sont désormais des **briques du club** — des modèles de bibliothèque, sans tournoi. La
// copie d'une édition se travaille au pilotage (« Assemblage »), là où l'on a un tournoi sous la
// main : c'est le partage déjà établi entre `gabarits` (le modèle) et `plan` (la copie).

import { useEffect, type ReactNode } from 'react'
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
import { VuePalmares } from '../palmares/VuePalmares'
import { Departs } from '../departs/Departs'
import { Duels } from '../duels/Duels'
import { Ecrans } from '../ecrans/Ecrans'
import { Exports } from '../exports/Exports'
import { Gabarits } from '../gabarits/Gabarits'
import { Assemblage } from '../patrimoine/Assemblage'
import { BlasonsBibliotheque, CategoriesBibliotheque } from '../patrimoine/Bibliotheque'
import { Deroule } from '../deroule/Deroule'
import { Formats } from '../patrimoine/Formats'
import { ImportClubs } from '../patrimoine/ImportClubs'
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
import { SuiviDeroule } from '../suivi-deroule/SuiviDeroule'
import { Supervision } from '../supervision/Supervision'
import { RechercheArcher } from '../recherche/RechercheArcher'
import { useSessionAdminStore } from '../../shared/stores/sessionAdminStore'
import { AideEcran } from '../../shared/ui/AideEcran'
import { ChangerDeRole } from '../../shared/ui/ChangerDeRole'
import { BandeauContexte } from './BandeauContexte'
import { ConnexionAdmin } from './ConnexionAdmin'
import { AIDE_ECRANS, type DestinationAdminId } from './aide-ecrans'
import {
  AXES,
  BESOIN_TOURNOI,
  AXE_PAR_DESTINATION,
  analyserSegmentsAdmin,
  contextePilotage,
  destinationParDefaut,
  destinationValide,
  segmentsAdmin,
  type Axe,
} from './axes'
import { analyserChemin, construireChemin } from '../../shared/navigation/routeur'
import { naviguer, useChemin } from '../../shared/navigation/useChemin'
import { BadgeStatut } from '../competition/BadgeStatut'
import { GestionTournois } from '../tournois/Tournois'

// L'appli admin (coquille) n'est présentée qu'à un admin connecté. Elle n'est atteinte que par la
// **porte Admin** de l'écran d'accueil (E00US017, ADR-0042) : sans session, on affiche donc le
// **login** (E10US002) — plus la consultation publique, désormais sa propre porte. La lecture
// publique passe par la porte « Téléphone », le scoreur et la tablette par les leurs.
export function CoquilleAdmin() {
  const estAdmin = useSessionAdminStore((s) => s.jeton) !== null
  if (estAdmin) return <Coquille />
  // Mise en page de la planche A01, variante **A — « formulaire sobre plein cadre »** (retenue au
  // questionnaire du 04/08/2026, E17US003) : une **colonne centrée**, et non une carte posée dans
  // l'angle haut-gauche de l'écran. Le titre « Administration » disparaît : l'en-tête d'application
  // dit déjà « Kervignarc », et le bandeau de la carte dit ce qu'on y fait — la planche ne porte
  // qu'un seul de ces trois niveaux.
  return (
    <div className="connexion">
      <section className="carte carte--connexion">
        <ConnexionAdmin />
      </section>
      {/* Retour explicite à l'écran des portes (A01, retour maquettes du 04/08/2026 : *« il manque
          peut-être une possibilité de choisir un autre écran… il faut pouvoir sélectionner un rôle de
          l'appareil »*).
          L'échappatoire **existait déjà** — « Changer de rôle », dans l'en-tête, depuis E00US017 —
          mais elle est délibérément discrète (action rare, ton neutre) et n'a donc pas été vue là où
          on la cherche : sur le seul écran où l'on peut s'être trompé de porte. On ne la déplace pas,
          on la **redouble ici**, au pied du formulaire, avec les mots de la question posée.
          Depuis E17US003 elle est **hors de la carte et centrée**, comme sur la planche : dedans,
          elle se lisait comme une action du formulaire. */}
      <p className="connexion__echappatoire">
        <ChangerDeRole libelle="← Choisir un autre appareil" />
      </p>
    </div>
  )
}

// ————————————————————————————————————————————————————————————————————————————————————————————————
// Coquille admin : accueil des trois axes, puis sidebar de l'axe courant + zone principale.
// ————————————————————————————————————————————————————————————————————————————————————————————————

function Coquille() {
  const tournois = useTournois()
  // **Le tournoi, l'axe et la destination vivent tous les trois dans l'adresse** (E14US003) :
  // `/admin` = l'accueil qui choisit l'axe, `/admin/12/pilotage/supervision` = un écran précis sur un
  // tournoi précis. **Rien n'est dupliqué en état local** — c'est ce qui fait qu'un `F5` revient
  // exactement où l'on était, et qu'un lien s'ouvre sur la même vue.
  //
  // Le tournoi était resté en `useState` dans la première version : l'axe et l'écran survivaient au
  // rechargement, mais pas leur **sujet** — donc 21 destinations sur 24 retombaient sur « choisissez
  // un tournoi ». Défaut relevé par les cinq axes de revue.
  const chemin = useChemin()
  const {
    tournoiId,
    axe: axeActif,
    destinationDemandee,
  } = analyserSegmentsAdmin(analyserChemin(chemin).segments)

  // Version **fraîche** du tournoi courant : après un démarrer/terminer, la liste est invalidée et
  // re-lue, ce qui rafraîchit le statut ici (badge, accueil) sans état local à synchroniser.
  const courant =
    tournoiId === null ? null : (tournois.data?.find((t) => t.id === tournoiId) ?? null)

  // Toute navigation d'administration passe par ici : le tournoi courant est **reconduit** d'un écran
  // à l'autre et d'un axe à l'autre, puisqu'il fait partie de l'adresse.
  const allerA = (axe: Axe, destination: DestinationAdminId, tournoi = tournoiId) =>
    naviguer(
      construireChemin({ monde: 'admin', segments: segmentsAdmin(tournoi, axe, destination) }),
    )

  const entrerDansAxe = (axe: Axe) => allerA(axe, destinationParDefaut(axe))

  // Choisir un tournoi **depuis l'accueil** le rend courant et ouvre son **pilotage** sur l'accueil
  // contextualisé (`D-20`) : c'est le geste « je viens m'occuper de ce tournoi ».
  const entrerDansTournoi = (t: Tournoi) =>
    allerA('pilotage', destinationParDefaut('pilotage'), t.id)

  // Changer de tournoi **depuis le sélecteur**, à l'intérieur d'un axe : on reste où l'on travaille.
  // Ne pas arracher l'admin de son écran est le pendant de `P-3` — la priorité d'affichage guide,
  // elle ne contraint pas. Le badge de statut, lui, se met à jour en direct.
  const changerTournoi = (t: Tournoi) => {
    if (axeActif !== null && active !== undefined) allerA(axeActif, active.id, t.id)
  }

  // Chaque destination = une **feature autonome** montée par **une seule entrée** (guide §8). Les
  // Le besoin d'un tournoi est déclaré dans `axes.ts` (`BESOIN_TOURNOI`), pas ici : tant qu'il
  // vivait dans ce tableau local, aucun test ne pouvait vérifier « aucune destination de l'atelier
  // n'exige un tournoi » — l'invariant même qui solde DETTE-023. `rendu` n'est appelé que lorsque
  // ce garde est satisfait ; il est défini dans le composant pour fermer sur `courant`.
  const destinations: {
    // Typé par l'union des `id` d'aide (et non `string`) : ajouter une destination sans son entrée
    // dans `AIDE_ECRANS` ne compile plus — la couverture « une aide par écran » (E14US002) est
    // garantie par `tsc`, plus par une vérification manuelle.
    // `tournoi` est exclue : elle a quitté les destinations pour l'accueil (l'assemblage).
    id: Exclude<DestinationAdminId, 'tournoi'>
    libelle: string
    rendu: () => ReactNode
  }[] = [
    {
      id: 'accueil',
      libelle: 'Accueil (tableau de bord)',
      // Accueil-tableau de bord contextualisé (E14US001, `D-20`) : la « photo d'ensemble » du tournoi
      // courant (frise, checklist, chiffres). Destination d'ouverture par défaut (`destinationParDefaut`).
      rendu: () => courant && <Accueil tournoi={courant} />,
    },
    {
      id: 'categories',
      libelle: 'Catégories',
      // Brique du **club** depuis E01US023 : plus aucun tournoi requis (DETTE-023 résorbée).
      rendu: () => <CategoriesBibliotheque />,
    },
    {
      id: 'blasons',
      libelle: 'Blasons',
      rendu: () => <BlasonsBibliotheque />,
    },
    {
      id: 'formats',
      libelle: 'Formats (déroulés)',
      // Le déroulé type d'une compétition (ADR-0060 §5). Ce qui se réutilise d'une année sur
      // l'autre est le **format**, pas la phase — celle-ci porte un statut et un rang propres à
      // une édition.
      rendu: () => <Formats />,
    },
    {
      id: 'deroule',
      libelle: 'Composer un déroulé',
      // L'atelier de composition (E01US024, ADR-0063) : là où un format se **fabrique**, se
      // **regarde** et se **fait tourner**, alors que « Formats » n'en gère que la bibliothèque.
      // Sans tournoi, comme tout l'axe atelier.
      rendu: () => <Deroule />,
    },
    {
      id: 'assemblage',
      libelle: 'Assemblage',
      // La **copie** du patrimoine dans cette édition, et son retour (« rendre permanent »).
      // Au pilotage et non à l'atelier : ici on travaille sur un tournoi, pas sur le club.
      // Les écrans d'édition des **copies** du tournoi sont montés ici, sous l'assemblage : sans
      // eux, libérer les briques aurait fait **perdre** la possibilité d'ajuster une catégorie pour
      // une seule édition — or c'est précisément ce que le CA promet (« modification locale au
      // tournoi »). L'assemblage les alimente, ces écrans les corrigent.
      rendu: () =>
        courant && (
          <>
            <Assemblage tournoiId={courant.id} />
            <Categories tournoiId={courant.id} />
            <Blasons tournoiId={courant.id} />
          </>
        ),
    },
    {
      id: 'gabarits',
      libelle: 'Gabarits (modèles)',
      rendu: () => <Gabarits />,
    },
    {
      id: 'plan',
      libelle: 'Plan de salle',
      rendu: () => courant && <PlanDeSalle tournoiId={courant.id} />,
    },
    {
      id: 'bareme',
      libelle: 'Barème & validation',
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
      // Séquence des phases du moteur (E05US001, ADR-0045) : élimination directe / placement après
      // la qualification. Juste après « Barème & validation » — c'est la suite de la définition du
      // format (la qualification, elle, se règle sur cet écran-là).
      rendu: () => courant && <Phases tournoiId={courant.id} />,
    },
    {
      id: 'departs',
      libelle: 'Départs & tarifs',
      // Les départs (créneaux) portent le tarif (E02US004, ADR-0017).
      rendu: () => courant && <Departs tournoiId={courant.id} />,
    },
    {
      id: 'clubs',
      libelle: 'Clubs',
      // Le référentiel et son **import en masse** (E01US023) vont ensemble : c'est le même geste
      // — peupler la liste des clubs voisins — à deux échelles.
      rendu: () => (
        <>
          <Clubs />
          <ImportClubs />
        </>
      ),
    },
    {
      id: 'scoreurs',
      libelle: 'Scoreurs',
      rendu: () => courant && <Scoreurs tournoiId={courant.id} />,
    },
    {
      id: 'inscriptions',
      libelle: 'Inscriptions',
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
      // Nettoyage de la liste des inscrits (E02US005) : repérer les fiches en double et fusionner.
      // Juste après « Inscriptions » — c'est la suite naturelle du travail sur la liste.
      rendu: () => courant && <Doublons tournoiId={courant.id} />,
    },
    {
      id: 'placement',
      libelle: 'Placement',
      rendu: () => courant && <Placement tournoiId={courant.id} />,
    },
    {
      id: 'duels',
      libelle: 'Plan de duels',
      // Ajustement du placement des duellistes d'une phase de tableau (E03US009, ADR-0048). L'écran
      // choisit lui-même la **phase** (comme « Placement » choisit le départ) : la navigation reste
      // par `useState` local, sans react-router (arbitrage du 18/07/2026 — cf. en-tête de fichier).
      rendu: () => courant && <Duels tournoiId={courant.id} />,
    },
    {
      id: 'paiements',
      libelle: 'Paiements',
      rendu: () => courant && <Paiements tournoiId={courant.id} />,
    },
    {
      id: 'postes',
      libelle: 'Postes de cible',
      rendu: () => courant && <Postes tournoiId={courant.id} />,
    },
    {
      id: 'jeu-essai',
      libelle: 'Jeu d’essai',
      // Outil de démo/QA (E15US001) : peupler le tournoi courant OU instancier un scénario qui crée
      // son propre tournoi — d'où son `false` dans `BESOIN_TOURNOI` (la brique « peupler » gère
      // l'absence de tournoi courant). À l'instanciation, on **sort de l'atelier** pour aller piloter
      // le tournoi qui vient de naître : c'est le geste « j'ai fabriqué, je vais m'en servir ».
      rendu: () => (
        <JeuEssai
          tournoiId={tournoiId}
          onTournoiInstancie={(id) => {
            allerA('pilotage', destinationParDefaut('pilotage'), id)
          }}
        />
      ),
    },
    {
      id: 'simulation',
      libelle: 'Simulation',
      // Cockpit de simulation (E15US003) : rejoue le tournoi courant en accéléré **sans rien
      // enregistrer** (bot pausable + reprise en main + vues cible/archer/scoreur/public). Ne simule
      // qu'un tournoi avant démarrage (garde-fou serveur) — d'où sa place dans « Préparation ».
      rendu: () => courant && <Simulation tournoiId={courant.id} />,
    },
    {
      id: 'supervision',
      libelle: 'Supervision',
      rendu: () => courant && <Supervision tournoiId={courant.id} />,
    },
    {
      // Écrans de salle (E07US004) : la **préparation** — créer, nommer, distribuer le code,
      // régler le déroulé de vues. Le **pilotage** (imposer une vue) est dans la supervision : on
      // prépare à froid, on pilote à chaud, là où l'on voit déjà l'état de la salle.
      id: 'ecrans',
      libelle: 'Écrans de salle',
      rendu: () => courant && <Ecrans tournoiId={courant.id} />,
    },
    {
      // Suivi du déroulé (E07US004) : la **deuxième surface** du schéma à braquets — le même
      // dessin que l'atelier, rempli par la réalité, à un poste PC plutôt que projeté.
      id: 'suivi-deroule',
      libelle: 'Suivi du déroulé',
      rendu: () => courant && <SuiviDeroule tournoiId={courant.id} />,
    },
    {
      // Feu vert / lancer le tour (E12US002) : le geste central du jour J — voir en continu ce qui
      // est prêt à partir, puis faire partir les duels prêts (les postes/écrans sont prévenus).
      id: 'feu-vert',
      libelle: 'Feu vert',
      rendu: () => courant && <FeuVert tournoiId={courant.id} />,
    },
    {
      id: 'completude',
      libelle: 'Complétude',
      // « Qu'est-ce qui manque pour finir ? » (E12US005) + contrôle avant de terminer. Le statut
      // pilote l'apparition du bouton « Terminer » (uniquement *en cours*).
      rendu: () => courant && <Completude tournoiId={courant.id} statut={courant.statut} />,
    },
    {
      id: 'classement',
      libelle: 'Classement en direct',
      rendu: () => courant && <VueClassement tournoiId={courant.id} admin />,
    },
    {
      id: 'palmares',
      libelle: 'Palmarès',
      // Le classement **final** (E06US004) : podiums par catégorie puis classement complet, et
      // l'export PDF qu'on affiche au mur. Distinct de « Classement en direct », qui est celui de
      // la qualification — l'organisateur consulte les deux, à deux moments de la journée.
      rendu: () => courant && <VuePalmares tournoiId={courant.id} />,
    },
    {
      id: 'exports',
      libelle: 'Exports',
      // Listes imprimables du jour J (E09US003) : placement (accueil) et club & paiement (admin).
      // Destination prévue au §7.1, désormais matérialisée sur le socle PDF (E09US001).
      rendu: () => courant && <Exports tournoiId={courant.id} />,
    },
    {
      id: 'archive',
      libelle: 'Archive',
      // Paquet ZIP de fin de tournoi (E11US003) : instantané SQLite + CSV + PDF régénérés + manifeste,
      // au choix (cases à cocher). Destination prévue au §7.1, désormais matérialisée.
      rendu: () => courant && <Archive tournoiId={courant.id} />,
    },
  ]

  // Accueil de l'admin : aucun axe ouvert. Il porte le choix de l'axe **et** l'assemblage (la liste
  // des tournois, leur création, leur cycle de vie) — l'ancienne destination « Tournoi », qui
  // n'appartenait à aucun des trois axes puisqu'elle *crée* l'objet sur lequel deux d'entre eux
  // travaillent.
  // ⚠️ Tout ce qui suit est calculé **avant** le retour anticipé de l'accueil : le `useEffect` de
  // correction d'adresse ne peut pas vivre après un `return` conditionnel (règles des hooks). Les
  // valeurs ne sont exploitées que dans la branche « un axe est ouvert ».
  const axe = AXES.find((a) => a.axe === axeActif) ?? null
  const dansAxe =
    axeActif === null ? [] : destinations.filter((d) => AXE_PAR_DESTINATION[d.id] === axeActif)
  // La destination vient de l'adresse, **validée contre les destinations de cet axe** : sans ça,
  // `/admin/atelier/supervision` afficherait un écran de pilotage sous l'intitulé « Atelier ».
  // À défaut, **l'ouverture de l'axe** — et non `dansAxe[0]`, qui ne coïncidait avec elle que par
  // l'ordre de déclaration : réordonner la sidebar aurait silencieusement changé l'écran d'entrée.
  const demandee = destinationValide(
    destinationDemandee,
    dansAxe.map((d) => d.id),
  )
  const ouverture = axe === null ? null : destinationParDefaut(axe.axe)
  const active =
    dansAxe.find((d) => d.id === demandee) ?? dansAxe.find((d) => d.id === ouverture) ?? dansAxe[0]

  // L'adresse doit dire la vérité **aussi à l'intérieur de l'admin** : `/admin/atelier/supervision`
  // affichait l'ouverture de l'atelier sous une adresse mensongère, qu'un signet ou une capture de
  // recette aurait figée. Même politique qu'`App` sur les mondes, même `replaceState` (correction
  // subie, à ne pas empiler dans l'historique).
  const chemAttendu =
    axe === null || active === undefined
      ? null
      : construireChemin({
          monde: 'admin',
          segments: segmentsAdmin(tournoiId, axe.axe, active.id),
        })
  useEffect(() => {
    if (chemAttendu !== null && chemin !== chemAttendu) {
      naviguer(chemAttendu, { remplacer: true })
    }
  }, [chemin, chemAttendu])

  if (axeActif === null) {
    // Les deux dérivations sont **pures et testées** dans `axes.ts` : elles portent des règles
    // invisibles au rendu (un tournoi *en pause* compte comme en cours) que seul un test tient.
    const liste = tournois.data ?? []
    const enCours = liste.filter((t) => t.statut === 'en_cours' || t.statut === 'en_pause').length
    const contexte = contextePilotage(liste)
    return (
      <div className="accueil-admin">
        <h2 className="accueil-admin__question">Que venez-vous faire ?</h2>
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
                {a.axe === 'pilotage' && contexte !== null && (
                  <span className="accueil-admin__contexte">{contexte}</span>
                )}
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

  // Un axe est ouvert : `axe` et `active` sont nécessairement définis (chaque axe a au moins une
  // destination, et `axeActif` vient d'être écarté du cas `null`).
  if (axe === null || active === undefined) return null

  const contenu =
    BESOIN_TOURNOI[active.id] && courant === null ? (
      // Depuis E01US023, **seuls** les axes à tournoi peuvent atteindre cet état : toutes les
      // destinations de l'atelier sont hors tournoi (DETTE-023 résorbée), donc le repli « cette
      // brique dépend encore d'un tournoi » n'a plus d'objet — et « ci-dessus » désigne bien, ici,
      // le sélecteur que l'axe affiche.
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
        {/* Bandeau de contexte (A02, 04/08/2026) : sur quel tournoi, quel départ, quel écran. Rendu
            au-dessus de l'aide et du contenu, à la façon dont la coquille rend déjà l'aide — un seul
            point d'insertion couvre les 24 destinations. Il n'apparaît que si l'axe travaille sur un
            tournoi **et** qu'un tournoi est choisi : sinon l'écran affiche déjà « choisissez un
            tournoi », et un bandeau vide au-dessus ne ferait que répéter le manque. */}
        {axe.besoinTournoi && courant !== null && (
          <BandeauContexte
            tournoi={courant}
            axeLibelle={axe.libelle}
            ecranLibelle={active.libelle}
            avecDepart={axe.axe === 'pilotage'}
          />
        )}
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
