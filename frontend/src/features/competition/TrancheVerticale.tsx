// Écran de la tranche verticale démontrable (E00US011) + gestion des tournois (E01US001,
// E01US002).
//
// Fil rouge : créer/choisir un tournoi (nom, date, lieu, type officiel/non) → inscrire un
// archer → le placer sur une cible → saisir un score → voir le classement se mettre à jour
// **en live**. La gestion des tournois (liste, édition des métadonnées, cycle de vie
// brouillon → en cours → terminé, suppression) est réservée à l'admin (E10US001) ; la lecture
// reste publique. Volontairement minimal et évolutif : les vrais écrans d'administration
// (placement, saisie tactile, écran projeté) viendront comme features dédiées.

import { useState } from 'react'
import { ConnexionAdmin } from '../admin/ConnexionAdmin'
import { useDeconnexionAdmin } from '../admin/hooks'
import { Archers } from '../archers/Archers'
import { BaremeQualification } from '../bareme/BaremeQualification'
import { GrainValidation } from '../grain-validation/GrainValidation'
import { Blasons } from '../blasons/Blasons'
import { Categories } from '../categories/Categories'
import { useCategories } from '../categories/hooks'
import { Clubs } from '../clubs/Clubs'
import { useClubs } from '../clubs/hooks'
import { Departs } from '../departs/Departs'
import { Gabarits } from '../gabarits/Gabarits'
import { PlanDeSalle } from '../gabarits/PlanDeSalle'
import { Placement } from '../placement/Placement'
import { EspaceScoreur } from '../scoreur-session/EspaceScoreur'
import { Scoreurs } from '../scoreurs/Scoreurs'
import { ErreurApi } from '../../shared/api/client'
import { useSessionAdminStore } from '../../shared/stores/sessionAdminStore'
import type { StatutTournoi, Tournoi, TypeTournoi } from './api'
import { TableClassement } from './TableClassement'
import {
  useAjouterArcher,
  useClassement,
  useCreerTournoi,
  useDemarrerTournoi,
  useModifierTournoi,
  useSupprimerTournoi,
  useTerminerTournoi,
  useTournois,
} from './hooks'

export function TrancheVerticale() {
  const [selection, setSelection] = useState<Tournoi | null>(null)
  const tournois = useTournois()

  // Version **fraîche** du tournoi sélectionné : après un démarrer/terminer, la liste est
  // invalidée et re-lue, ce qui rafraîchit ici le statut sans état local à synchroniser.
  const selectionne =
    selection === null ? null : (tournois.data?.find((t) => t.id === selection.id) ?? selection)

  if (selectionne === null) {
    return (
      <>
        <GestionTournois tournois={tournois.data ?? []} onChoisi={setSelection} />
        {/* L'entrée du scoreur, à côté de la liste des tournois : il ouvre l'app sur son téléphone
            et tape son code, sans passer par l'admin (E10US003). */}
        <EspaceScoreur />
      </>
    )
  }
  return <Competition tournoi={selectionne} onRetour={() => setSelection(null)} />
}

// La **création/édition** et le **cycle de vie** d'un tournoi sont des fonctions d'administration
// (E10US002) : réservées à un admin connecté. La **lecture** (liste des tournois, pour en rouvrir
// un) reste publique. Sans session admin, on présente l'écran de connexion à la place du formulaire.
function GestionTournois({
  tournois,
  onChoisi,
}: {
  tournois: Tournoi[]
  onChoisi: (t: Tournoi) => void
}) {
  const estAdmin = useSessionAdminStore((s) => s.jeton) !== null

  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">Tournois</h2>

      {estAdmin ? <FormulaireNouveauTournoi onChoisi={onChoisi} /> : <ConnexionAdmin />}

      {tournois.length > 0 && (
        <>
          <h3 className="carte__soustitre">Tournois existants</h3>
          <ul className="liste-tournois">
            {tournois.map((t) => (
              <LigneTournoi key={t.id} tournoi={t} estAdmin={estAdmin} onChoisi={onChoisi} />
            ))}
          </ul>
        </>
      )}
    </section>
  )
}

// Une ligne de la liste : ouvrir le tournoi, plus (admin) l'éditer ou le supprimer. La
// suppression demande une **confirmation explicite** (deux temps) et reste indisponible tant que
// le tournoi est **en cours** (il faut d'abord le terminer, garanti aussi côté serveur, E01US002).
function LigneTournoi({
  tournoi,
  estAdmin,
  onChoisi,
}: {
  tournoi: Tournoi
  estAdmin: boolean
  onChoisi: (t: Tournoi) => void
}) {
  const [edition, setEdition] = useState(false)
  const [confirmationSuppression, setConfirmationSuppression] = useState(false)
  const supprimer = useSupprimerTournoi()

  if (edition) {
    return (
      <li>
        <FormulaireEditionTournoi tournoi={tournoi} onTermine={() => setEdition(false)} />
      </li>
    )
  }

  const enCours = tournoi.statut === 'en_cours'

  return (
    <li className="tournoi">
      <div className="tournoi__ligne">
        <button type="button" className="lien" onClick={() => onChoisi(tournoi)}>
          {tournoi.nom} — {tournoi.date}
          {tournoi.lieu ? ` · ${tournoi.lieu}` : ''} · {tournoi.type_tournoi.replace('_', ' ')}
        </button>
        <BadgeStatut statut={tournoi.statut} />
        {estAdmin && (
          <span className="tournoi__actions">
            <button type="button" className="bouton--discret" onClick={() => setEdition(true)}>
              Éditer
            </button>
            {confirmationSuppression ? (
              <>
                <button
                  type="button"
                  className="bouton--danger"
                  disabled={supprimer.isPending}
                  onClick={() => supprimer.mutate(tournoi.id)}
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
            ) : enCours ? (
              // Un tournoi en cours n'est pas supprimable (garanti aussi côté serveur, 409).
              // On l'explique par un **texte visible** plutôt qu'un `title` sur un bouton désactivé
              // (inatteignable au clavier / lecteur d'écran — le CDC vise WCAG AA).
              <span className="tournoi__note">Terminez le tournoi pour pouvoir le supprimer.</span>
            ) : (
              <button
                type="button"
                className="bouton--danger"
                onClick={() => setConfirmationSuppression(true)}
              >
                Supprimer
              </button>
            )}
          </span>
        )}
      </div>
      <MessageErreur erreur={supprimer.error} />
    </li>
  )
}

// Pastille de statut (cycle de vie du tournoi).
function BadgeStatut({ statut }: { statut: StatutTournoi }) {
  const libelles: Record<StatutTournoi, string> = {
    brouillon: 'Brouillon',
    en_cours: 'En cours',
    termine: 'Terminé',
  }
  return <span className={`badge badge--${statut.replace('_', '-')}`}>{libelles[statut]}</span>
}

function FormulaireNouveauTournoi({ onChoisi }: { onChoisi: (t: Tournoi) => void }) {
  const [nom, setNom] = useState('')
  const [date, setDate] = useState('')
  const [lieu, setLieu] = useState('')
  const [type, setType] = useState<TypeTournoi>('non_officiel')
  const creer = useCreerTournoi()
  const deconnexion = useDeconnexionAdmin()

  // Le tarif ne se fixe plus à la création du tournoi : il vit sur chaque départ (créneau), qui se
  // configure une fois le tournoi ouvert (E02US004, ADR-0017).
  const soumissionPossible = nom.trim() !== '' && date !== ''

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!soumissionPossible) return
    // Un 401 (session expirée) est géré centralement par le client HTTP (purge de session).
    creer.mutate(
      {
        nom,
        date,
        lieu: lieu.trim() || null,
        type_tournoi: type,
      },
      { onSuccess: onChoisi },
    )
  }

  return (
    <div>
      <h3 className="carte__soustitre">Nouveau tournoi</h3>
      <form className="formulaire formulaire--colonne" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={nom}
          onChange={(e) => setNom(e.target.value)}
          placeholder="Nom du tournoi"
          aria-label="Nom du tournoi"
        />
        <input
          className="formulaire__champ"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          aria-label="Date du tournoi"
        />
        <input
          className="formulaire__champ"
          value={lieu}
          onChange={(e) => setLieu(e.target.value)}
          placeholder="Lieu (facultatif)"
          aria-label="Lieu du tournoi"
        />
        <select
          className="formulaire__champ"
          value={type}
          onChange={(e) => setType(e.target.value as TypeTournoi)}
          aria-label="Type de tournoi"
        >
          <option value="non_officiel">Non officiel</option>
          <option value="officiel">Officiel</option>
        </select>
        <button type="submit" disabled={creer.isPending || !soumissionPossible}>
          Créer
        </button>
      </form>
      <MessageErreur erreur={creer.error} />
      <button type="button" className="lien" onClick={() => deconnexion.mutate()}>
        Se déconnecter (admin)
      </button>
    </div>
  )
}

// Édition des métadonnées d'un tournoi (nom, date, lieu, type) — autorisée quel que soit le
// statut ; le cycle de vie évolue par ailleurs via Démarrer/Terminer.
function FormulaireEditionTournoi({
  tournoi,
  onTermine,
}: {
  tournoi: Tournoi
  onTermine: () => void
}) {
  const [nom, setNom] = useState(tournoi.nom)
  const [date, setDate] = useState(tournoi.date)
  const [lieu, setLieu] = useState(tournoi.lieu ?? '')
  const [type, setType] = useState<TypeTournoi>(tournoi.type_tournoi)
  const modifier = useModifierTournoi()

  const soumissionPossible = nom.trim() !== '' && date !== ''

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!soumissionPossible) return
    modifier.mutate(
      {
        id: tournoi.id,
        entree: {
          nom,
          date,
          lieu: lieu.trim() || null,
          type_tournoi: type,
        },
      },
      { onSuccess: onTermine },
    )
  }

  return (
    <div>
      <h3 className="carte__soustitre">Modifier le tournoi</h3>
      <form className="formulaire formulaire--colonne" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={nom}
          onChange={(e) => setNom(e.target.value)}
          placeholder="Nom du tournoi"
          aria-label="Nom du tournoi"
        />
        <input
          className="formulaire__champ"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          aria-label="Date du tournoi"
        />
        <input
          className="formulaire__champ"
          value={lieu}
          onChange={(e) => setLieu(e.target.value)}
          placeholder="Lieu (facultatif)"
          aria-label="Lieu du tournoi"
        />
        <select
          className="formulaire__champ"
          value={type}
          onChange={(e) => setType(e.target.value as TypeTournoi)}
          aria-label="Type de tournoi"
        >
          <option value="non_officiel">Non officiel</option>
          <option value="officiel">Officiel</option>
        </select>
        <div className="formulaire__actions">
          <button type="submit" disabled={modifier.isPending || !soumissionPossible}>
            Enregistrer
          </button>
          <button type="button" className="bouton--discret" onClick={onTermine}>
            Annuler
          </button>
        </div>
      </form>
      <MessageErreur erreur={modifier.error} />
    </div>
  )
}

// Consultation d'un tournoi. Le **classement** est public (lecture seule). Les **actions
// d'écriture** (cycle de vie, inscrire, marquer) ne sont exposées qu'à un admin connecté
// (E10US001) — un spectateur voit le classement sans aucun contrôle.
function Competition({ tournoi, onRetour }: { tournoi: Tournoi; onRetour: () => void }) {
  const estAdmin = useSessionAdminStore((s) => s.jeton) !== null
  const classement = useClassement(tournoi.id)

  return (
    <section className="carte carte--large">
      <button type="button" className="lien" onClick={onRetour}>
        ← Tous les tournois
      </button>
      <h2 className="carte__titre">
        {tournoi.nom} <BadgeStatut statut={tournoi.statut} />
      </h2>

      {estAdmin && <CycleDeVie tournoi={tournoi} />}

      {/* Les départs (créneaux) portent le tarif : leur configuration remplace l'ancien tarif au
          niveau du tournoi (E02US004, ADR-0017). */}
      {estAdmin && <Departs tournoiId={tournoi.id} />}

      {estAdmin && <Categories tournoiId={tournoi.id} />}

      {estAdmin && <Blasons tournoiId={tournoi.id} />}

      {estAdmin && <PlanDeSalle tournoiId={tournoi.id} />}

      {estAdmin && <Gabarits />}

      {/* Comme les gabarits modèles, le référentiel des clubs est **global** : il ne prend pas de
          tournoi. Il servira à rattacher les archers sans ressaisie (E02US002). */}
      {estAdmin && <Clubs />}

      {estAdmin && <BaremeQualification tournoiId={tournoi.id} />}

      {/* Juste après le barème : le grain se règle sur la même phase, et n'a de sens qu'une fois
          le barème défini (E01US015). */}
      {estAdmin && <GrainValidation tournoiId={tournoi.id} />}

      {/* Scoreurs (E10US003) : module de préparation, on déclare les 3-4 valideurs et leurs codes.
          Redéfinissable même tournoi en cours (D-14). */}
      {estAdmin && <Scoreurs tournoiId={tournoi.id} />}

      {estAdmin ? (
        <InscriptionArcher tournoiId={tournoi.id} />
      ) : (
        <p className="carte__etat">
          Consultation en lecture seule. Connectez-vous en admin pour saisir.
        </p>
      )}

      {/* Juste après le formulaire d'inscription : on inscrit, puis on corrige — et c'est là que
          le « club inconnu » signalé à la ligne du dessus devient réparable (E02US003). */}
      {estAdmin && <Archers tournoiId={tournoi.id} />}

      {/* Placement sur les cibles (E03US004) : une fois les archers inscrits sur des départs, on
          ajuste le plan de cibles créneau par créneau, au glisser-déposer. */}
      {estAdmin && <Placement tournoiId={tournoi.id} />}

      <h3 className="carte__soustitre">Classement en direct</h3>
      {classement.isPending && <p className="carte__etat">Chargement…</p>}
      {classement.isError && (
        <p className="carte__etat carte__etat--erreur" role="alert">
          Classement injoignable — {classement.error.message}
        </p>
      )}
      {classement.data && (
        <TableClassement tournoiId={tournoi.id} lignes={classement.data.lignes} admin={estAdmin} />
      )}
    </section>
  )
}

// Cycle de vie (E01US002) : démarrer (brouillon → en cours), terminer (en cours → terminé).
// Chaque bouton n'apparaît qu'au statut où il a un sens ; le serveur reste l'autorité (409).
function CycleDeVie({ tournoi }: { tournoi: Tournoi }) {
  const demarrer = useDemarrerTournoi()
  const terminer = useTerminerTournoi()

  return (
    <div className="cycle-de-vie">
      {tournoi.statut === 'brouillon' && (
        <button
          type="button"
          disabled={demarrer.isPending}
          onClick={() => demarrer.mutate(tournoi.id)}
        >
          Démarrer le tournoi
        </button>
      )}
      {tournoi.statut === 'en_cours' && (
        <button
          type="button"
          disabled={terminer.isPending}
          onClick={() => terminer.mutate(tournoi.id)}
        >
          Terminer le tournoi
        </button>
      )}
      {tournoi.statut === 'termine' && <p className="carte__etat">Ce tournoi est terminé.</p>}
      <MessageErreur erreur={demarrer.error ?? terminer.error} />
    </div>
  )
}

// Inscription d'un archer (E02US002). Deux asymétries à ne pas « corriger » par mégarde :
//
//  - la **catégorie est obligatoire** (sans elle, l'archer n'est ni classable ni plaçable) tandis
//    que le **club ne l'est pas** : « Club inconnu » veut dire « pas encore su », jamais « aucun
//    club » — en FFTA tout licencié en a un (ADR-0014). On inscrit quand même, et on le signale ;
//  - un homonyme est **signalé, pas refusé** : le backend rend 409 `homonyme_archer`, l'admin
//    tranche (père et fils portent les mêmes nom, prénom et club). Le second envoi porte la
//    confirmation. C'est le serveur qui arbitre — un simple avertissement d'UI se contournerait.
function InscriptionArcher({ tournoiId }: { tournoiId: number }) {
  const [nomArcher, setNomArcher] = useState('')
  const [prenomArcher, setPrenomArcher] = useState('')
  const [clubId, setClubId] = useState('')
  const [categorieId, setCategorieId] = useState('')
  const clubs = useClubs()
  const categories = useCategories(tournoiId)
  const ajouter = useAjouterArcher(tournoiId)

  const incomplet = nomArcher.trim() === '' || prenomArcher.trim() === '' || categorieId === ''
  const homonymeSignale =
    ajouter.error instanceof ErreurApi && ajouter.error.code === 'homonyme_archer'

  // Le 409 porte sur **une identité précise** (nom, prénom, club). Dès que l'un des trois change,
  // le signalement ne s'y applique plus : on l'efface, sinon « Inscrire quand même » confirmerait
  // un archer que le serveur n'a jamais examiné — et le doublon que cette US refuse passerait
  // justement par le bouton prévu pour l'autoriser.
  //
  // `reset()` plutôt que de comparer à la clé signalée : comparer exigerait de réimplémenter en TS
  // le repli casse/accents de `domain.club.cle_nom`, soit une 2ᵉ implémentation d'une règle de
  // domaine — précisément ce que `cle_identite` refuse côté backend en réutilisant `cle_nom`.
  // Ici, savoir « est-ce que ça a changé » suffit ; nul besoin de savoir « est-ce la même clé ».
  const surIdentite = (poser: (valeur: string) => void) => (valeur: string) => {
    if (ajouter.error !== null) ajouter.reset()
    poser(valeur)
  }

  const inscrire = (autoriserHomonyme: boolean) => {
    ajouter.mutate(
      {
        nom: nomArcher,
        prenom: prenomArcher,
        categorie_id: Number(categorieId),
        club_id: clubId === '' ? null : Number(clubId),
        autoriser_homonyme: autoriserHomonyme,
      },
      // Ni le club ni la catégorie ne sont réinitialisés : on inscrit souvent plusieurs archers
      // du même club et de la même catégorie à la suite, à la table d'inscription.
      {
        onSuccess: () => {
          setNomArcher('')
          setPrenomArcher('')
        },
      },
    )
  }

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (incomplet) return
    inscrire(false)
  }

  return (
    <>
      <form className="formulaire" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={nomArcher}
          onChange={(e) => surIdentite(setNomArcher)(e.target.value)}
          placeholder="Nom de l'archer"
          aria-label="Nom de l'archer"
        />
        <input
          className="formulaire__champ"
          value={prenomArcher}
          onChange={(e) => surIdentite(setPrenomArcher)(e.target.value)}
          placeholder="Prénom de l'archer"
          aria-label="Prénom de l'archer"
        />
        <select
          className="formulaire__champ"
          value={categorieId}
          onChange={(e) => setCategorieId(e.target.value)}
          aria-label="Catégorie de l'archer"
        >
          <option value="">Choisir une catégorie…</option>
          {(categories.data ?? []).map((categorie) => (
            <option key={categorie.id} value={categorie.id}>
              {categorie.libelle}
            </option>
          ))}
        </select>
        <select
          className="formulaire__champ"
          value={clubId}
          onChange={(e) => surIdentite(setClubId)(e.target.value)}
          aria-label="Club de l'archer"
        >
          <option value="">Club inconnu</option>
          {(clubs.data ?? []).map((club) => (
            <option key={club.id} value={club.id}>
              {club.nom}
            </option>
          ))}
        </select>
        <button type="submit" disabled={ajouter.isPending || incomplet}>
          Inscrire
        </button>
      </form>
      {/* `isSuccess` et non `data ?? []` : tant que la requête court, `data` est `undefined` et
          le message s'afficherait à tort sur un tournoi qui a bel et bien des catégories. */}
      {categories.isSuccess && categories.data.length === 0 && (
        <p className="carte__etat">
          Aucune catégorie dans ce tournoi : créez-en une avant d'inscrire un archer.
        </p>
      )}
      {/* Rendu **hors** `MessageErreur`, délibérément : ce bloc porte une action et un ton neutre
          (un doublon probable n'est pas une erreur — l'inscription reste possible). C'est pourquoi
          il n'a pas le modificateur `--erreur`. À reprendre avec E00US013, qui factorisera les
          briques d'UI ([DETTE-004](../../../../docs/dette.md)) : ce n'est pas une 10ᵉ copie de
          `MessageErreur`, donc un grep sur ce nom ne le trouvera pas. */}
      {homonymeSignale ? (
        <div className="carte__etat" role="alert">
          <p>{ajouter.error?.message}</p>
          <button
            type="button"
            onClick={() => inscrire(true)}
            disabled={ajouter.isPending || incomplet}
          >
            Inscrire quand même
          </button>
        </div>
      ) : (
        <MessageErreur erreur={ajouter.error} />
      )}
    </>
  )
}

function MessageErreur({ erreur }: { erreur: Error | null }) {
  if (erreur === null) return null
  const message = erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
  return (
    <p className="carte__etat carte__etat--erreur" role="alert">
      {message}
    </p>
  )
}
