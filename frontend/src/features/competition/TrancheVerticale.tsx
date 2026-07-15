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
import { BaremeQualification } from '../bareme/BaremeQualification'
import { GrainValidation } from '../grain-validation/GrainValidation'
import { Blasons } from '../blasons/Blasons'
import { Categories } from '../categories/Categories'
import { useCategories } from '../categories/hooks'
import { Clubs } from '../clubs/Clubs'
import { useClubs } from '../clubs/hooks'
import { Gabarits } from '../gabarits/Gabarits'
import { PlanDeSalle } from '../gabarits/PlanDeSalle'
import { ErreurApi } from '../../shared/api/client'
import { useSessionAdminStore } from '../../shared/stores/sessionAdminStore'
import type { StatutTournoi, Tournoi, TypeTournoi } from './api'
import {
  centimesVersSaisieEuros,
  decrireTarif,
  decrireTarifParDepart,
  saisieEurosVersCentimes,
} from './format'
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
    return <GestionTournois tournois={tournois.data ?? []} onChoisi={setSelection} />
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
          {tournoi.lieu ? ` · ${tournoi.lieu}` : ''} · {tournoi.type_tournoi.replace('_', ' ')} ·{' '}
          {decrireTarif(tournoi.tarif_depart_centimes)}
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
  const [tarif, setTarif] = useState('')
  const creer = useCreerTournoi()
  const deconnexion = useDeconnexionAdmin()

  // Le tarif est **facultatif** : un champ vide crée un tournoi sans tarif défini (`null`), ce qui
  // n'est pas « gratuit ». Une saisie présente doit en revanche être un montant valide.
  const tarifCentimes = tarif.trim() === '' ? null : saisieEurosVersCentimes(tarif)
  const tarifValide = tarif.trim() === '' || tarifCentimes !== null
  const soumissionPossible = nom.trim() !== '' && date !== '' && tarifValide

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
        tarif_depart_centimes: tarifCentimes,
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
        <ChampTarif valeur={tarif} onChange={setTarif} />
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

// Le tarif d'un départ (E01US010) : saisi en **euros**, transmis en **centimes**. Le champ est
// facultatif — vide = « pas de tarif défini », ce qui n'est pas « gratuit » (saisir 0 pour cela).
function ChampTarif({ valeur, onChange }: { valeur: string; onChange: (v: string) => void }) {
  const saisi = valeur.trim() !== ''
  const invalide = saisi && saisieEurosVersCentimes(valeur) === null

  return (
    <label className="formulaire__libelle">
      Tarif d'un départ (facultatif)
      <input
        className="formulaire__champ"
        inputMode="decimal"
        value={valeur}
        onChange={(e) => onChange(e.target.value)}
        placeholder="ex. 8,10 — laisser vide si non défini"
        aria-label="Tarif d'un départ en euros"
      />
      {invalide ? (
        <span className="carte__etat carte__etat--erreur" role="alert">
          Montant en euros attendu, avec au plus 2 décimales (ex. 8,10).
        </span>
      ) : (
        // L'astuce ne sert qu'au champ vide : une fois le tarif saisi, elle donnerait
        // « Gratuit · saisir "0" pour un tournoi gratuit ».
        <span className="carte__etat">
          {saisi
            ? decrireTarif(saisieEurosVersCentimes(valeur))
            : 'Aucun tarif défini · saisir « 0 » pour un tournoi gratuit'}
        </span>
      )}
    </label>
  )
}

// Édition des métadonnées d'un tournoi (nom, date, lieu, type, tarif) — autorisée quel que soit le
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
  // Semé avec la valeur serveur : l'édition **remplace** le tarif, donc un champ laissé tel quel
  // doit être réémis à l'identique — sinon rouvrir le formulaire effacerait le tarif.
  const [tarif, setTarif] = useState(
    tournoi.tarif_depart_centimes === null
      ? ''
      : centimesVersSaisieEuros(tournoi.tarif_depart_centimes),
  )
  const modifier = useModifierTournoi()

  const tarifCentimes = tarif.trim() === '' ? null : saisieEurosVersCentimes(tarif)
  const tarifValide = tarif.trim() === '' || tarifCentimes !== null
  const soumissionPossible = nom.trim() !== '' && date !== '' && tarifValide

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
          tarif_depart_centimes: tarifCentimes,
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
        <ChampTarif valeur={tarif} onChange={setTarif} />
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
      {/* Le tarif est une information publique : c'est ce que paiera l'archer (E01US010). */}
      <p className="carte__etat">{decrireTarifParDepart(tournoi.tarif_depart_centimes)}</p>

      {estAdmin && <CycleDeVie tournoi={tournoi} />}

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

      {estAdmin ? (
        <InscriptionArcher tournoiId={tournoi.id} />
      ) : (
        <p className="carte__etat">
          Consultation en lecture seule. Connectez-vous en admin pour saisir.
        </p>
      )}

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
          onChange={(e) => setNomArcher(e.target.value)}
          placeholder="Nom de l'archer"
          aria-label="Nom de l'archer"
        />
        <input
          className="formulaire__champ"
          value={prenomArcher}
          onChange={(e) => setPrenomArcher(e.target.value)}
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
          onChange={(e) => setClubId(e.target.value)}
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
      {(categories.data ?? []).length === 0 && (
        <p className="carte__etat">
          Aucune catégorie dans ce tournoi : créez-en une avant d'inscrire un archer.
        </p>
      )}
      {homonymeSignale ? (
        <div className="carte__etat" role="alert">
          <p>{ajouter.error?.message}</p>
          <button type="button" onClick={() => inscrire(true)} disabled={ajouter.isPending}>
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
