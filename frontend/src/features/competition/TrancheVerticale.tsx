// Écran de la tranche verticale démontrable (E00US011) + création de tournoi (E01US001).
//
// Fil rouge : créer/choisir un tournoi (nom, date, lieu, type officiel/non) → inscrire un
// archer → le placer sur une cible → saisir un score → voir le classement se mettre à jour
// **en live**. Volontairement minimal et jetable/évolutif : les vrais écrans d'administration
// (liste/édition, placement, saisie tactile, écran projeté) viendront comme features dédiées.

import { useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
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

function CreationTournoi({ onChoisi }: { onChoisi: (t: Tournoi) => void }) {
  const [nom, setNom] = useState('')
  const [date, setDate] = useState('')
  const [lieu, setLieu] = useState('')
  const [type, setType] = useState<TypeTournoi>('non_officiel')
  const creer = useCreerTournoi()
  const tournois = useTournois()

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (nom.trim() === '' || date === '') return
    creer.mutate(
      { nom, date, lieu: lieu.trim() || null, type_tournoi: type },
      { onSuccess: onChoisi },
    )
  }

  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">Nouveau tournoi</h2>
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

function Competition({ tournoiId, nom }: { tournoiId: number; nom: string }) {
  const [nomArcher, setNomArcher] = useState('')
  const classement = useClassement(tournoiId)
  const ajouter = useAjouterArcher(tournoiId)

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (nomArcher.trim() === '') return
    ajouter.mutate(nomArcher, { onSuccess: () => setNomArcher('') })
  }

  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">{nom}</h2>

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

      <h3 className="carte__soustitre">Classement en direct</h3>
      {classement.isPending && <p className="carte__etat">Chargement…</p>}
      {classement.isError && (
        <p className="carte__etat carte__etat--erreur">
          Classement injoignable — {classement.error.message}
        </p>
      )}
      {classement.data && <TableClassement tournoiId={tournoiId} lignes={classement.data.lignes} />}
    </section>
  )
}

function MessageErreur({ erreur }: { erreur: Error | null }) {
  if (erreur === null) return null
  const message = erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
  return <p className="carte__etat carte__etat--erreur">{message}</p>
}
