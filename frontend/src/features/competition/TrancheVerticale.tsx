// Écran de la tranche verticale démontrable (E00US011) + création de tournoi (E01US001).
//
// Fil rouge : créer/choisir un tournoi (nom, date, lieu, type officiel/non) → inscrire un
// archer → le placer sur une cible → saisir un score → voir le classement se mettre à jour
// **en live**. Volontairement minimal et jetable/évolutif : les vrais écrans d'administration
// (liste/édition, placement, saisie tactile, écran projeté) viendront comme features dédiées.

import { useState } from 'react'
import { ConnexionAdmin } from '../admin/ConnexionAdmin'
import { useDeconnexionAdmin } from '../admin/hooks'
import { ErreurApi } from '../../shared/api/client'
import { useSessionAdminStore } from '../../shared/stores/sessionAdminStore'
import type { Tournoi, TypeTournoi } from './api'
import { TableClassement } from './TableClassement'
import { useAjouterArcher, useClassement, useCreerTournoi, useTournois } from './hooks'

export function TrancheVerticale() {
  const [tournoi, setTournoi] = useState<Tournoi | null>(null)

  if (tournoi === null) {
    return <CreationTournoi onChoisi={setTournoi} />
  }
  return <Competition tournoiId={tournoi.id} nom={tournoi.nom} />
}

// La **création** d'un tournoi est une fonction d'administration (E10US002) : réservée à un
// admin connecté. La **lecture** (liste des tournois existants, pour en rouvrir un) reste
// publique. Sans session admin, on présente l'écran de connexion à la place du formulaire.
function CreationTournoi({ onChoisi }: { onChoisi: (t: Tournoi) => void }) {
  const jeton = useSessionAdminStore((s) => s.jeton)
  const tournois = useTournois()

  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">Tournois</h2>

      {jeton ? <FormulaireNouveauTournoi onChoisi={onChoisi} /> : <ConnexionAdmin />}

      {tournois.data && tournois.data.length > 0 && (
        <>
          <h3 className="carte__soustitre">Tournois existants</h3>
          <ul className="liste-tournois">
            {tournois.data.map((t) => (
              <li key={t.id}>
                <button type="button" className="lien" onClick={() => onChoisi(t)}>
                  {t.nom} — {t.date}
                  {t.lieu ? ` · ${t.lieu}` : ''} · {t.type_tournoi.replace('_', ' ')}
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}

function FormulaireNouveauTournoi({ onChoisi }: { onChoisi: (t: Tournoi) => void }) {
  const [nom, setNom] = useState('')
  const [date, setDate] = useState('')
  const [lieu, setLieu] = useState('')
  const [type, setType] = useState<TypeTournoi>('non_officiel')
  const creer = useCreerTournoi()
  const deconnexion = useDeconnexionAdmin()

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (nom.trim() === '' || date === '') return
    // Un 401 (session expirée) est géré centralement par le client HTTP (purge de session).
    creer.mutate(
      { nom, date, lieu: lieu.trim() || null, type_tournoi: type },
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
        <button type="submit" disabled={creer.isPending || nom.trim() === '' || date === ''}>
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

// Consultation d'un tournoi. Le **classement** est public (lecture seule). Les **actions
// d'écriture** (inscrire, placer, marquer) ne sont exposées qu'à un admin connecté (E10US001) —
// un spectateur voit le classement sans aucun contrôle de saisie.
function Competition({ tournoiId, nom }: { tournoiId: number; nom: string }) {
  const estAdmin = useSessionAdminStore((s) => s.jeton) !== null
  const classement = useClassement(tournoiId)

  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">{nom}</h2>

      {estAdmin ? (
        <InscriptionArcher tournoiId={tournoiId} />
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
        <TableClassement tournoiId={tournoiId} lignes={classement.data.lignes} admin={estAdmin} />
      )}
    </section>
  )
}

function InscriptionArcher({ tournoiId }: { tournoiId: number }) {
  const [nomArcher, setNomArcher] = useState('')
  const ajouter = useAjouterArcher(tournoiId)

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (nomArcher.trim() === '') return
    ajouter.mutate(nomArcher, { onSuccess: () => setNomArcher('') })
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
        <button type="submit" disabled={ajouter.isPending || nomArcher.trim() === ''}>
          Inscrire
        </button>
      </form>
      <MessageErreur erreur={ajouter.error} />
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
