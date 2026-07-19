// Gestion des tournois (E01US001, E01US002) — feature extraite de `competition/TrancheVerticale.tsx`
// lors de la coquille admin (E00US015). Le fichier `TrancheVerticale.tsx` enfouissait cette fonction
// dans l'écran d'une autre (guide §8 : « aucune fonction n'est enfouie dans le fichier d'une autre ») ;
// elle vit désormais dans sa propre feature.
//
// Périmètre : créer / éditer / lister / supprimer un tournoi et piloter son **cycle de vie**
// (brouillon → en cours → terminé). La **création et le cycle de vie** sont réservés à l'admin
// (E10US002) ; la **lecture** (liste, pour rouvrir un tournoi ou consulter son classement public)
// reste publique — sans session admin, on présente l'écran de connexion à la place du formulaire.
//
// La couche données (types + hooks React Query) reste dans `competition/` : c'est un hub partagé
// (archers, placement en dépendent aussi), qu'on ne déplace pas au titre de cette US.

import { useState } from 'react'
import { ConnexionAdmin } from '../admin/ConnexionAdmin'
import { useDeconnexionAdmin } from '../admin/hooks'
import { ErreurApi } from '../../shared/api/client'
import { useSessionAdminStore } from '../../shared/stores/sessionAdminStore'
import type { StatutTournoi, Tournoi, TypeTournoi } from '../competition/api'
import {
  useCreerTournoi,
  useDemarrerTournoi,
  useModifierTournoi,
  useSupprimerTournoi,
  useTerminerTournoi,
  useTournois,
} from '../competition/hooks'

// Destination « Tournoi » de la coquille (E00US015) et accueil public (liste en lecture seule).
// Fetch interne : la feature est autonome, on ne lui passe pas la liste. Un tournoi sélectionné
// (`selectionneId`) est mis en évidence et, côté admin, coiffé de son cycle de vie.
export function GestionTournois({
  selectionneId,
  onChoisi,
}: {
  selectionneId: number | null
  onChoisi: (t: Tournoi) => void
}) {
  const estAdmin = useSessionAdminStore((s) => s.jeton) !== null
  const tournois = useTournois()

  // Version **fraîche** du tournoi courant : après un démarrer/terminer, la liste est invalidée et
  // re-lue, ce qui rafraîchit le statut ici sans état local à synchroniser.
  const courant =
    selectionneId === null ? null : (tournois.data?.find((t) => t.id === selectionneId) ?? null)

  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">Tournois</h2>

      {/* Sans ce bloc, une liste injoignable (backend coupé) se réduirait à « aucun tournoi » — un
          faux vide qui fait croire à une base vide plutôt qu'à une panne réseau. */}
      {tournois.isError && (
        <p className="carte__etat carte__etat--erreur" role="alert">
          Liste des tournois injoignable — {tournois.error.message}
        </p>
      )}

      {/* Cycle de vie du tournoi courant, en tête : c'est ici, sur la destination « Tournoi », que
          se pilote son avancement (l'ancien écran monolithique le mêlait aux autres modules). */}
      {estAdmin && courant !== null && (
        <div className="tournoi-courant">
          <h3 className="carte__soustitre">
            {courant.nom} <BadgeStatut statut={courant.statut} />
          </h3>
          <CycleDeVie tournoi={courant} />
        </div>
      )}

      {estAdmin ? <FormulaireNouveauTournoi onChoisi={onChoisi} /> : <ConnexionAdmin />}

      {(tournois.data ?? []).length > 0 && (
        <>
          <h3 className="carte__soustitre">Tournois existants</h3>
          <ul className="liste-tournois">
            {(tournois.data ?? []).map((t) => (
              <LigneTournoi
                key={t.id}
                tournoi={t}
                estAdmin={estAdmin}
                selectionne={t.id === selectionneId}
                onChoisi={onChoisi}
              />
            ))}
          </ul>
        </>
      )}
    </section>
  )
}

// Une ligne de la liste : ouvrir le tournoi, plus (admin) l'éditer ou le supprimer. La suppression
// demande une **confirmation explicite** (deux temps) et reste indisponible tant que le tournoi est
// **en cours** (il faut d'abord le terminer, garanti aussi côté serveur, E01US002).
function LigneTournoi({
  tournoi,
  estAdmin,
  selectionne,
  onChoisi,
}: {
  tournoi: Tournoi
  estAdmin: boolean
  selectionne: boolean
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
    <li className={selectionne ? 'tournoi tournoi--selectionne' : 'tournoi'}>
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
              // Un tournoi en cours n'est pas supprimable (garanti aussi côté serveur, 409). On
              // l'explique par un **texte visible** plutôt qu'un `title` sur un bouton désactivé
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

// Pastille de statut (cycle de vie du tournoi). Exportée : la coquille (E00US015) l'affiche dans son
// sélecteur de tournoi, au-dessus de la navigation.
export function BadgeStatut({ statut }: { statut: StatutTournoi }) {
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

// Édition des métadonnées d'un tournoi (nom, date, lieu, type) — autorisée quel que soit le statut ;
// le cycle de vie évolue par ailleurs via Démarrer/Terminer.
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

// Cycle de vie (E01US002) : démarrer (brouillon → en cours), terminer (en cours → terminé). Chaque
// bouton n'apparaît qu'au statut où il a un sens ; le serveur reste l'autorité (409).
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

// DETTE-004 (docs/dette.md) : copie conforme de ce composant, une par feature. La coquille (E00US015)
// a **relocalisé** ici la copie de l'ancien `TrancheVerticale.tsx` (le décompte global est inchangé).
// À extraire dans `shared/` — E00US013, quand toutes les copies seront remplacées d'un bloc.
function MessageErreur({ erreur }: { erreur: Error | null }) {
  if (erreur === null) return null
  const message = erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
  return (
    <p className="carte__etat carte__etat--erreur" role="alert">
      {message}
    </p>
  )
}
