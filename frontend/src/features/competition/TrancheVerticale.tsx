// Écran de la tranche verticale démontrable (E00US011).
//
// Fil rouge du walking skeleton, de bout en bout : créer un tournoi → inscrire un archer →
// le placer sur une cible → saisir un score → voir le classement se mettre à jour **en live**.
// Volontairement minimal et jetable/évolutif : les vrais écrans (placement, saisie tactile,
// écran projeté) viendront comme features dédiées.

import { useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import { TableClassement } from './TableClassement'
import { useAjouterArcher, useClassement, useCreerTournoi } from './hooks'

export function TrancheVerticale() {
  const [tournoi, setTournoi] = useState<{ id: number; nom: string } | null>(null)

  if (tournoi === null) {
    return <CreationTournoi onCree={setTournoi} />
  }
  return <Competition tournoiId={tournoi.id} nom={tournoi.nom} />
}

function CreationTournoi({ onCree }: { onCree: (t: { id: number; nom: string }) => void }) {
  const [nom, setNom] = useState('')
  const creer = useCreerTournoi()

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (nom.trim() === '') return
    creer.mutate(nom, { onSuccess: onCree })
  }

  return (
    <section className="carte">
      <h2 className="carte__titre">Nouveau tournoi</h2>
      <form className="formulaire" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={nom}
          onChange={(e) => setNom(e.target.value)}
          placeholder="Nom du tournoi"
          aria-label="Nom du tournoi"
        />
        <button type="submit" disabled={creer.isPending || nom.trim() === ''}>
          Créer
        </button>
      </form>
      <MessageErreur erreur={creer.error} />
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
