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
// prévoit mais qui n'existent pas encore (Identité, Complétude, Validation, Podiums, Paiements,
// Exports, Archive, Audit, recherche) ne sont **pas** matérialisées par des entrées vides — elles
// arriveront avec leur US. De même, les 7 statuts d'ADR-0026 (E01US017) ne sont pas encore livrés :
// l'accueil contextualisé s'appuie sur les **3 statuts actuels** (brouillon / en_cours / termine).
// « Supervision » (E12US001) est livrée et l'accueil d'un tournoi *en cours* pointe dessus ;
// « Résultats » n'ayant pas encore d'écran dédié, un tournoi *terminé* retombe sur le classement.

import { useState, type ReactNode } from 'react'
import { Archers } from '../archers/Archers'
import { NouvelArcher } from '../archers/NouvelArcher'
import { BaremeQualification } from '../bareme/BaremeQualification'
import { Blasons } from '../blasons/Blasons'
import { Categories } from '../categories/Categories'
import { useCategories } from '../categories/hooks'
import { Clubs } from '../clubs/Clubs'
import type { StatutTournoi, Tournoi } from '../competition/api'
import { useClassement, useTournois } from '../competition/hooks'
import { TableClassement } from '../competition/TableClassement'
import { Departs } from '../departs/Departs'
import { Gabarits } from '../gabarits/Gabarits'
import { PlanDeSalle } from '../gabarits/PlanDeSalle'
import { GrainValidation } from '../grain-validation/GrainValidation'
import { Placement } from '../placement/Placement'
import { Postes } from '../postes/Postes'
import { EspaceScoreur } from '../scoreur-session/EspaceScoreur'
import { Scoreurs } from '../scoreurs/Scoreurs'
import { Supervision } from '../supervision/Supervision'
import { useSessionAdminStore } from '../../shared/stores/sessionAdminStore'
import { BadgeStatut, GestionTournois } from '../tournois/Tournois'

// L'appli admin (coquille) n'est présentée qu'à un admin connecté. Sans session, on reste sur la
// **consultation publique** (E10US001) — liste des tournois en lecture seule, classement public, et
// les entrées de rôle (scoreur, poste) pour les autres tablettes.
export function CoquilleAdmin() {
  const estAdmin = useSessionAdminStore((s) => s.jeton) !== null
  return estAdmin ? <Coquille /> : <AccueilPublic />
}

// ————————————————————————————————————————————————————————————————————————————————————————————————
// Coquille admin : sélecteur de tournoi + sidebar groupée par temps + zone principale.
// ————————————————————————————————————————————————————————————————————————————————————————————————

type Temps = 'preparation' | 'jourj'

const GROUPES: { temps: Temps; libelle: string }[] = [
  { temps: 'preparation', libelle: 'Préparation' },
  { temps: 'jourj', libelle: 'Jour J' },
]

// Destination par défaut selon le statut (`D-20`). Un tournoi *en cours* ouvre sur la **supervision**
// (E12US001) — l'écran du jour J. « Résultats » (termine) n'ayant pas encore d'écran propre, un
// tournoi *terminé* retombe sur le classement en direct.
function destinationParDefaut(statut: StatutTournoi): { id: string; groupe: Temps } {
  switch (statut) {
    case 'brouillon':
      return { id: 'tournoi', groupe: 'preparation' }
    case 'en_cours':
      return { id: 'supervision', groupe: 'jourj' }
    case 'termine':
      return { id: 'classement', groupe: 'jourj' }
  }
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
    const defaut = destinationParDefaut(t.statut)
    setDestinationActive(defaut.id)
    setGroupeOuvert(defaut.groupe)
  }

  // Chaque destination = une **feature autonome** montée par **une seule entrée** (guide §8). Les
  // destinations `besoinTournoi` exigent un tournoi courant ; les autres (Gabarits, Clubs) sont des
  // référentiels **globaux**, hors tournoi. Défini dans le composant pour fermer sur `courant` /
  // `choisirTournoi` ; `rendu` n'est appelé que lorsque le garde `besoinTournoi` est satisfait.
  const destinations: {
    id: string
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
      id: 'placement',
      libelle: 'Placement',
      groupe: 'preparation',
      besoinTournoi: true,
      rendu: () => courant && <Placement tournoiId={courant.id} />,
    },
    {
      id: 'postes',
      libelle: 'Postes de cible',
      groupe: 'preparation',
      besoinTournoi: true,
      rendu: () => courant && <Postes tournoiId={courant.id} />,
    },
    {
      id: 'supervision',
      libelle: 'Supervision',
      groupe: 'jourj',
      besoinTournoi: true,
      rendu: () => courant && <Supervision tournoiId={courant.id} />,
    },
    {
      id: 'classement',
      libelle: 'Classement en direct',
      groupe: 'jourj',
      besoinTournoi: true,
      rendu: () => courant && <VueClassement tournoiId={courant.id} admin />,
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

      <div className="coquille__contenu">{contenu}</div>
    </div>
  )
}

// ————————————————————————————————————————————————————————————————————————————————————————————————
// Consultation publique (E10US001) : sans session admin, la lecture reste ouverte.
// ————————————————————————————————————————————————————————————————————————————————————————————————

function AccueilPublic() {
  const [selection, setSelection] = useState<Tournoi | null>(null)

  return (
    <div className="app__contenu--colonnes">
      {/* En public, `GestionTournois` présente l'écran de connexion + la liste en lecture seule. */}
      <GestionTournois selectionneId={selection?.id ?? null} onChoisi={setSelection} />

      {selection && (
        <section className="carte carte--large">
          <button type="button" className="lien" onClick={() => setSelection(null)}>
            ← Tous les tournois
          </button>
          <h2 className="carte__titre">
            {selection.nom} <BadgeStatut statut={selection.statut} />
          </h2>
          <VueClassement tournoiId={selection.id} admin={false} />
        </section>
      )}

      <aside className="carte">
        {/* L'entrée du scoreur : il ouvre l'app sur son téléphone et tape son code, sans passer par
            l'admin (E10US003). */}
        <EspaceScoreur />
        {/* Entrée « poste de cible » (E04US001) : normalement on arrive par le QR de sa cible
            (`?poste=<code>`, E09US008) ; ce lien de secours ouvre l'écran de poste sans QR — une
            fois la tablette rattachée, l'app y va d'elle-même (App.tsx), ce lien ne resert plus. */}
        <p className="carte__etat">
          <a className="lien" href="?poste">
            Cette tablette est un poste de cible ›
          </a>
        </p>
      </aside>
    </div>
  )
}

// Classement de qualification en direct — public (lecture seule) ou admin (colonne « Placer »).
// Partagé par la destination « Classement » de la coquille et la consultation publique. Un filtre
// par catégorie (E06US001) restreint l'affichage à une catégorie sans changer les rangs : le rang
// scratch (global) reste celui du classement complet — on **voit** une catégorie sans perdre la
// position d'ensemble.
function VueClassement({ tournoiId, admin }: { tournoiId: number; admin: boolean }) {
  const [categorieId, setCategorieId] = useState<number | undefined>(undefined)
  const categories = useCategories(tournoiId)
  const classement = useClassement(tournoiId, categorieId)

  return (
    <>
      <h3 className="carte__soustitre">Classement en direct</h3>
      <label className="classement-filtre">
        Catégorie{' '}
        <select
          value={categorieId ?? ''}
          onChange={(e) =>
            setCategorieId(e.target.value === '' ? undefined : Number(e.target.value))
          }
        >
          <option value="">Toutes catégories</option>
          {(categories.data ?? []).map((categorie) => (
            <option key={categorie.id} value={categorie.id}>
              {categorie.libelle}
            </option>
          ))}
        </select>
      </label>
      {classement.isPending && <p className="carte__etat">Chargement…</p>}
      {classement.isError && (
        <p className="carte__etat carte__etat--erreur" role="alert">
          Classement injoignable — {classement.error.message}
        </p>
      )}
      {classement.data && (
        <TableClassement tournoiId={tournoiId} lignes={classement.data.lignes} admin={admin} />
      )}
    </>
  )
}
