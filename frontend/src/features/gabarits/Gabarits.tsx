// Gestion des gabarits de salle (E01US007) — réservée à l'admin (montée sous `estAdmin`).
//
// Un gabarit décrit un **plan de cibles réutilisable** (indépendant d'un tournoi). Tableau +
// création + édition depuis la ligne (E00US016) (nom, nombre de cibles, plafond d'archers par cible) + suppression à
// confirmation. À la création, le **plafond** (1 à 4, défaut 4) s'applique à toutes les cibles ;
// l'ajustement cible par cible est livré (E01US008). Les **couloirs de tir** (A/B/C/D) se
// déduisent du plafond côté serveur (champ `position`, cf. glossaire et DETTE-042).

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import type { Gabarit, NouveauGabarit } from './api'
import { decrireCouloirs } from './format'
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
        <div className="table-defilement">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Nom</th>
                <th scope="col">Cibles</th>
                <th scope="col">Couloirs de tir</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            {gabarits.data.map((gabarit) => (
              <LigneGabarit key={gabarit.id} gabarit={gabarit} />
            ))}
          </table>
        </div>
      )}
    </section>
  )
}

// Nom, cibles, couloirs, actions — la largeur d'une ligne de détail ou du formulaire d'édition.
const COLONNES = 4

function LigneGabarit({ gabarit }: { gabarit: Gabarit }) {
  const [edition, setEdition] = useState(false)
  const [confirmationSuppression, setConfirmationSuppression] = useState(false)
  const supprimer = useSupprimerGabarit()

  // Un `<tbody>` par gabarit : la ligne et son erreur de suppression se tiennent ensemble.
  if (edition) {
    return (
      <tbody>
        <tr>
          <td colSpan={COLONNES}>
            <FormulaireGabarit gabarit={gabarit} onTermine={() => setEdition(false)} />
          </td>
        </tr>
      </tbody>
    )
  }

  return (
    <tbody>
      <tr>
        <td className="gabarit__nom">{gabarit.nom}</td>
        <td>{gabarit.nb_cibles}</td>
        <td>{decrireCouloirs(gabarit)}</td>
        <td>
          <span className="gabarit__actions">
            <button
              type="button"
              className="bouton--discret"
              aria-label={`Éditer ${gabarit.nom}`}
              onClick={() => setEdition(true)}
            >
              Éditer
            </button>
            {confirmationSuppression ? (
              <>
                <button
                  type="button"
                  className="bouton--danger"
                  disabled={supprimer.isPending}
                  aria-label={`Confirmer la suppression de ${gabarit.nom}`}
                  onClick={() => supprimer.mutate(gabarit.id)}
                >
                  Confirmer la suppression
                </button>
                <button
                  type="button"
                  className="bouton--discret"
                  aria-label={`Annuler la suppression de ${gabarit.nom}`}
                  onClick={() => setConfirmationSuppression(false)}
                >
                  Annuler
                </button>
              </>
            ) : (
              <button
                type="button"
                className="bouton--danger"
                aria-label={`Supprimer ${gabarit.nom}`}
                onClick={() => setConfirmationSuppression(true)}
              >
                Supprimer
              </button>
            )}
          </span>
        </td>
      </tr>
      {supprimer.error !== null && (
        <tr>
          <td colSpan={COLONNES}>
            <MessageErreur erreur={supprimer.error} />
          </td>
        </tr>
      )}
    </tbody>
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
          aria-label="Couloirs de tir par cible"
        >
          {PLAFONDS.map((plafond) => (
            <option key={plafond} value={plafond}>
              Jusqu'à {plafond} couloir{plafond > 1 ? 's' : ''} de tir par cible
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
