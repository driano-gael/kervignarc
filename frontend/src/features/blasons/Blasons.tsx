// Gestion des blasons d'un tournoi (E01US005) — réservée à l'admin (montée sous `estAdmin`).
//
// Liste + création + édition (nom, taille, capacité) + suppression à confirmation. Un blason
// modélise l'occupation d'une cible : la **taille** est une fraction de place (]0, 1]) et la
// **capacité** le nombre d'archers admis (≥ 1). Les bornes sont validées côté serveur (domaine) ;
// un message d'erreur en rouge s'affiche si une valeur est refusée.

import { useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import type { Blason, NouveauBlason } from './api'
import { useBlasons, useCreerBlason, useModifierBlason, useSupprimerBlason } from './hooks'

export function Blasons({ tournoiId }: { tournoiId: number }) {
  const blasons = useBlasons(tournoiId)

  return (
    <section>
      <h3 className="carte__soustitre">Blasons</h3>
      <FormulaireBlason tournoiId={tournoiId} />
      {blasons.isError && <MessageErreur erreur={blasons.error} />}
      {blasons.data && blasons.data.length > 0 && (
        <ul className="liste-blasons">
          {blasons.data.map((blason) => (
            <LigneBlason key={blason.id} tournoiId={tournoiId} blason={blason} />
          ))}
        </ul>
      )}
    </section>
  )
}

function LigneBlason({ tournoiId, blason }: { tournoiId: number; blason: Blason }) {
  const [edition, setEdition] = useState(false)
  const [confirmationSuppression, setConfirmationSuppression] = useState(false)
  const supprimer = useSupprimerBlason(tournoiId)

  if (edition) {
    return (
      <li>
        <FormulaireBlason
          tournoiId={tournoiId}
          blason={blason}
          onTermine={() => setEdition(false)}
        />
      </li>
    )
  }

  return (
    <li className="blason">
      <div className="blason__ligne">
        <span className="blason__nom">{blason.nom}</span>
        <span className="blason__attributs">{decrire(blason)}</span>
        <span className="blason__actions">
          <button type="button" className="bouton--discret" onClick={() => setEdition(true)}>
            Éditer
          </button>
          {confirmationSuppression ? (
            <>
              <button
                type="button"
                className="bouton--danger"
                disabled={supprimer.isPending}
                onClick={() => supprimer.mutate(blason.id)}
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
      </div>
      <MessageErreur erreur={supprimer.error} />
    </li>
  )
}

// Décrit les attributs d'un blason pour l'affichage (taille de place · capacité).
function decrire(blason: Blason): string {
  const capacite = blason.capacite > 1 ? `${blason.capacite} archers` : '1 archer'
  return `taille ${blason.taille} · ${capacite}`
}

// Formulaire partagé création / édition : sans `blason` il crée, avec il édite.
function FormulaireBlason({
  tournoiId,
  blason,
  onTermine,
}: {
  tournoiId: number
  blason?: Blason
  onTermine?: () => void
}) {
  const enEdition = blason !== undefined
  const [nom, setNom] = useState(blason?.nom ?? '')
  const [taille, setTaille] = useState(blason ? String(blason.taille) : '1')
  const [capacite, setCapacite] = useState(blason ? String(blason.capacite) : '1')

  const creer = useCreerBlason(tournoiId)
  const modifier = useModifierBlason(tournoiId)
  const mutation = enEdition ? modifier : creer

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (nom.trim() === '') return
    const entree: NouveauBlason = {
      nom,
      taille: Number(taille),
      capacite: Number(capacite),
    }
    if (enEdition) {
      modifier.mutate({ id: blason.id, entree }, { onSuccess: onTermine })
    } else {
      // Création : on réinitialise le formulaire pour enchaîner une autre saisie.
      creer.mutate(entree, {
        onSuccess: () => {
          setNom('')
          setTaille('1')
          setCapacite('1')
        },
      })
    }
  }

  return (
    <div>
      {enEdition && <h4 className="carte__soustitre">Modifier le blason</h4>}
      <form className="formulaire formulaire--colonne" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={nom}
          onChange={(e) => setNom(e.target.value)}
          placeholder="Nom (ex. Trispot 40)"
          aria-label="Nom du blason"
        />
        <label className="formulaire__libelle">
          Taille (fraction de place, de 0 à 1)
          <input
            className="formulaire__champ"
            type="number"
            min="0"
            max="1"
            step="0.05"
            value={taille}
            onChange={(e) => setTaille(e.target.value)}
            aria-label="Taille du blason (fraction de place)"
          />
        </label>
        <label className="formulaire__libelle">
          Capacité (nombre d'archers)
          <input
            className="formulaire__champ"
            type="number"
            min="1"
            step="1"
            value={capacite}
            onChange={(e) => setCapacite(e.target.value)}
            aria-label="Capacité du blason (nombre d'archers)"
          />
        </label>
        <div className="formulaire__actions">
          <button type="submit" disabled={mutation.isPending || nom.trim() === ''}>
            {enEdition ? 'Enregistrer' : 'Ajouter le blason'}
          </button>
          {enEdition && (
            <button type="button" className="bouton--discret" onClick={onTermine}>
              Annuler
            </button>
          )}
        </div>
      </form>
      <MessageErreur erreur={mutation.error} />
    </div>
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
