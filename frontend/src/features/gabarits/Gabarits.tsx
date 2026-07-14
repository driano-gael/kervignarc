// Gestion des gabarits de salle (E01US007) — réservée à l'admin (montée sous `estAdmin`).
//
// Un gabarit décrit un **plan de cibles réutilisable** (indépendant d'un tournoi). Liste +
// création + édition (nom, nombre de cibles, plafond d'archers par cible) + suppression à
// confirmation. À la création, le **plafond** (1 à 4, défaut 4) s'applique à toutes les cibles ;
// l'ajustement cible par cible viendra en E01US008. Les positions (A/B/C/D) se déduisent du
// plafond côté serveur.

import { useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import type { Gabarit, NouveauGabarit } from './api'
import { decrire } from './format'
import { useCreerGabarit, useGabarits, useModifierGabarit, useSupprimerGabarit } from './hooks'

const PLAFONDS = [1, 2, 3, 4]

export function Gabarits() {
  const gabarits = useGabarits()

  return (
    <section>
      <h3 className="carte__soustitre">Gabarits de salle</h3>
      <FormulaireGabarit />
      {gabarits.isError && <MessageErreur erreur={gabarits.error} />}
      {gabarits.data && gabarits.data.length > 0 && (
        <ul className="liste-gabarits">
          {gabarits.data.map((gabarit) => (
            <LigneGabarit key={gabarit.id} gabarit={gabarit} />
          ))}
        </ul>
      )}
    </section>
  )
}

function LigneGabarit({ gabarit }: { gabarit: Gabarit }) {
  const [edition, setEdition] = useState(false)
  const [confirmationSuppression, setConfirmationSuppression] = useState(false)
  const supprimer = useSupprimerGabarit()

  if (edition) {
    return (
      <li>
        <FormulaireGabarit gabarit={gabarit} onTermine={() => setEdition(false)} />
      </li>
    )
  }

  return (
    <li className="gabarit">
      <div className="gabarit__ligne">
        <span className="gabarit__nom">{gabarit.nom}</span>
        <span className="gabarit__attributs">{decrire(gabarit)}</span>
        <span className="gabarit__actions">
          <button type="button" className="bouton--discret" onClick={() => setEdition(true)}>
            Éditer
          </button>
          {confirmationSuppression ? (
            <>
              <button
                type="button"
                className="bouton--danger"
                disabled={supprimer.isPending}
                onClick={() => supprimer.mutate(gabarit.id)}
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

// Formulaire partagé création / édition : sans `gabarit` il crée, avec il édite. À l'édition,
// le plafond est pré-rempli avec celui de la première cible (uniforme en E01US007).
function FormulaireGabarit({ gabarit, onTermine }: { gabarit?: Gabarit; onTermine?: () => void }) {
  const enEdition = gabarit !== undefined
  const [nom, setNom] = useState(gabarit?.nom ?? '')
  const [nbCibles, setNbCibles] = useState<string>(gabarit ? String(gabarit.nb_cibles) : '')
  const [capacite, setCapacite] = useState<number>(gabarit?.cibles[0]?.capacite ?? 4)

  const creer = useCreerGabarit()
  const modifier = useModifierGabarit()
  const mutation = enEdition ? modifier : creer

  const nbCiblesValide = Number.isInteger(Number(nbCibles)) && Number(nbCibles) >= 1
  const soumissionPossible = nom.trim() !== '' && nbCiblesValide

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!soumissionPossible) return
    const entree: NouveauGabarit = { nom, nb_cibles: Number(nbCibles), capacite }
    if (enEdition) {
      modifier.mutate({ id: gabarit.id, entree }, { onSuccess: onTermine })
    } else {
      // Création : on vide le formulaire pour enchaîner une autre saisie.
      creer.mutate(entree, {
        onSuccess: () => {
          setNom('')
          setNbCibles('')
          setCapacite(4)
        },
      })
    }
  }

  return (
    <div>
      {enEdition && <h4 className="carte__soustitre">Modifier le gabarit</h4>}
      <form className="formulaire formulaire--colonne" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={nom}
          onChange={(e) => setNom(e.target.value)}
          placeholder="Nom (ex. Salle municipale — 12 cibles)"
          aria-label="Nom du gabarit"
        />
        <input
          className="formulaire__champ"
          type="number"
          min={1}
          value={nbCibles}
          onChange={(e) => setNbCibles(e.target.value)}
          placeholder="Nombre de cibles"
          aria-label="Nombre de cibles"
        />
        <select
          className="formulaire__champ"
          value={capacite}
          onChange={(e) => setCapacite(Number(e.target.value))}
          aria-label="Plafond d'archers par cible"
        >
          {PLAFONDS.map((plafond) => (
            <option key={plafond} value={plafond}>
              Max {plafond} archer{plafond > 1 ? 's' : ''} par cible
            </option>
          ))}
        </select>
        <div className="formulaire__actions">
          <button type="submit" disabled={mutation.isPending || !soumissionPossible}>
            {enEdition ? 'Enregistrer' : 'Ajouter le gabarit'}
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
