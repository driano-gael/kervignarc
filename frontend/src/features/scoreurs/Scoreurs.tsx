// Définition des scoreurs d'un tournoi (E10US003) — réservé à l'admin (monté sous `estAdmin`).
//
// Liste (nom + **code** à distribuer) + création (le nom seul ; le serveur génère le code) +
// renommage (le code reste figé) + suppression à confirmation. 3 à 4 scoreurs suffisent pour ~30
// cibles (D-14) : c'est un petit module de **préparation** (P-6), redéfinissable même tournoi en
// cours. Le code est le sésame que le scoreur retape pour ouvrir sa session (« Espace scoreur »).
//
// Supprimer un scoreur **invalide sa session** côté serveur (il ne peut plus valider), mais la trace
// de ses validations passées est conservée (E10US005). Le code est affiché en clair : c'est un
// secret d'usage (pas un mot de passe), destiné à être imprimé et remis en main propre.

import { useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import type { Scoreur } from './api'
import { useCreerScoreur, useModifierScoreur, useScoreurs, useSupprimerScoreur } from './hooks'

export function Scoreurs({ tournoiId }: { tournoiId: number }) {
  const scoreurs = useScoreurs(tournoiId)

  return (
    <section>
      <h3 className="carte__soustitre">Scoreurs</h3>
      <p className="carte__etat">
        Déclarez les 3 à 4 personnes qui valideront les scores. Chacune reçoit un code à retaper
        dans « Espace scoreur » pour ouvrir sa session.
      </p>
      <FormulaireScoreur tournoiId={tournoiId} />
      {scoreurs.isError && <MessageErreur erreur={scoreurs.error} />}
      {scoreurs.data && scoreurs.data.length === 0 && (
        <p className="carte__etat">Aucun scoreur déclaré pour ce tournoi.</p>
      )}
      {scoreurs.data && scoreurs.data.length > 0 && (
        <ul className="liste-scoreurs">
          {scoreurs.data.map((scoreur) => (
            <LigneScoreur key={scoreur.id} tournoiId={tournoiId} scoreur={scoreur} />
          ))}
        </ul>
      )}
    </section>
  )
}

function LigneScoreur({ tournoiId, scoreur }: { tournoiId: number; scoreur: Scoreur }) {
  const [edition, setEdition] = useState(false)
  const [confirmationSuppression, setConfirmationSuppression] = useState(false)
  const supprimer = useSupprimerScoreur(tournoiId)

  if (edition) {
    return (
      <li>
        <FormulaireScoreur
          tournoiId={tournoiId}
          scoreur={scoreur}
          onTermine={() => setEdition(false)}
        />
      </li>
    )
  }

  return (
    <li className="scoreur">
      <div className="scoreur__ligne">
        <span className="scoreur__nom">{scoreur.nom}</span>
        {/* Code en évidence, en chiffres/lettres lisibles : c'est ce qu'on recopie sur le papier. */}
        <code className="scoreur__code">{scoreur.code}</code>
        <span className="scoreur__actions">
          <button type="button" className="bouton--discret" onClick={() => setEdition(true)}>
            Renommer
          </button>
          {confirmationSuppression ? (
            <>
              <button
                type="button"
                className="bouton--danger"
                disabled={supprimer.isPending}
                onClick={() => supprimer.mutate(scoreur.id)}
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
      {confirmationSuppression && (
        <p className="carte__etat">
          Sa session en cours sera coupée ; ses validations passées restent tracées.
        </p>
      )}
      <MessageErreur erreur={supprimer.error} />
    </li>
  )
}

// Formulaire partagé création / renommage : sans `scoreur` il crée (le serveur génère le code),
// avec il renomme (le code est figé, hors du formulaire).
function FormulaireScoreur({
  tournoiId,
  scoreur,
  onTermine,
}: {
  tournoiId: number
  scoreur?: Scoreur
  onTermine?: () => void
}) {
  const enEdition = scoreur !== undefined
  const [nom, setNom] = useState(scoreur?.nom ?? '')

  const creer = useCreerScoreur(tournoiId)
  const modifier = useModifierScoreur(tournoiId)
  const mutation = enEdition ? modifier : creer

  // Reprend la règle du domaine (nom non vide) pour éviter une requête vouée au 422 ; le serveur
  // reste l'autorité (revalidation à la frontière).
  const entreeValide = nom.trim() !== ''

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!entreeValide) return
    if (enEdition) {
      modifier.mutate({ scoreurId: scoreur.id, entree: { nom } }, { onSuccess: onTermine })
    } else {
      // Création : on réinitialise le champ pour enchaîner une autre déclaration.
      creer.mutate({ nom }, { onSuccess: () => setNom('') })
    }
  }

  return (
    <div>
      {enEdition && <h4 className="carte__soustitre">Renommer le scoreur</h4>}
      <form className="formulaire" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={nom}
          onChange={(e) => setNom(e.target.value)}
          placeholder="Nom du scoreur"
          aria-label="Nom du scoreur"
        />
        <div className="formulaire__actions">
          <button type="submit" disabled={mutation.isPending || !entreeValide}>
            {enEdition ? 'Enregistrer' : 'Ajouter le scoreur'}
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

// DETTE-004 (docs/dette.md) : énième copie conforme de ce composant, un par feature. À extraire dans
// `shared/` — E00US013. Non factorisée ici : le faire toucherait les autres features, hors périmètre.
function MessageErreur({ erreur }: { erreur: Error | null }) {
  if (erreur === null) return null
  const message = erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
  return (
    <p className="carte__etat carte__etat--erreur" role="alert">
      {message}
    </p>
  )
}
