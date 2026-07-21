// Référentiel des clubs (E02US001) — réservé à l'admin (monté sous `estAdmin`).
//
// Liste + création + renommage + suppression à confirmation. Le référentiel est **global** :
// aucun `tournoiId` en entrée, les clubs se réutilisent d'une compétition à l'autre. C'est ce
// qui évitera de ressaisir les clubs voisins à chaque tournoi, une fois les archers rattachés
// (E02US002).
//
// L'unicité du nom (casse **et accents** repliés) est vérifiée côté serveur : un doublon rend un 409, affiché
// tel quel — le message du serveur nomme le club déjà présent.

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import type { Club, NouveauClub } from './api'
import { useClubs, useCreerClub, useModifierClub, useSupprimerClub } from './hooks'

export function Clubs() {
  const clubs = useClubs()

  return (
    <section>
      <h3 className="carte__soustitre">Clubs</h3>
      <FormulaireClub />
      {clubs.isError && <MessageErreur erreur={clubs.error} />}
      {clubs.data && clubs.data.length === 0 && (
        <p className="carte__etat">Aucun club dans le référentiel.</p>
      )}
      {clubs.data && clubs.data.length > 0 && (
        <ul className="liste-clubs">
          {clubs.data.map((club) => (
            <LigneClub key={club.id} club={club} />
          ))}
        </ul>
      )}
    </section>
  )
}

function LigneClub({ club }: { club: Club }) {
  const [edition, setEdition] = useState(false)
  const [confirmationSuppression, setConfirmationSuppression] = useState(false)
  const supprimer = useSupprimerClub()

  if (edition) {
    return (
      <li>
        <FormulaireClub club={club} onTermine={() => setEdition(false)} />
      </li>
    )
  }

  return (
    <li className="club">
      <div className="club__ligne">
        <span className="club__nom">{club.nom}</span>
        <span className="club__actions">
          <button type="button" className="bouton--discret" onClick={() => setEdition(true)}>
            Renommer
          </button>
          {confirmationSuppression ? (
            <>
              <button
                type="button"
                className="bouton--danger"
                disabled={supprimer.isPending}
                onClick={() => supprimer.mutate(club.id)}
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

// Formulaire partagé création / renommage : sans `club` il crée, avec il renomme.
function FormulaireClub({ club, onTermine }: { club?: Club; onTermine?: () => void }) {
  const enEdition = club !== undefined
  const [nom, setNom] = useState(club?.nom ?? '')

  const creer = useCreerClub()
  const modifier = useModifierClub()
  const mutation = enEdition ? modifier : creer

  // Reprend la règle du domaine (nom non vide) pour éviter d'envoyer une requête vouée au 422 ;
  // le serveur reste l'autorité (revalidation à la frontière, unicité comprise).
  const entreeValide = nom.trim() !== ''

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!entreeValide) return
    const entree: NouveauClub = { nom }
    if (enEdition) {
      modifier.mutate({ id: club.id, entree }, { onSuccess: onTermine })
    } else {
      // Création : on réinitialise le formulaire pour enchaîner une autre saisie.
      creer.mutate(entree, { onSuccess: () => setNom('') })
    }
  }

  return (
    <div>
      {enEdition && <h4 className="carte__soustitre">Renommer le club</h4>}
      <form className="formulaire" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={nom}
          onChange={(e) => setNom(e.target.value)}
          placeholder="Nom (ex. Compagnie d'Arc de Fougères)"
          aria-label="Nom du club"
        />
        <div className="formulaire__actions">
          <button type="submit" disabled={mutation.isPending || !entreeValide}>
            {enEdition ? 'Enregistrer' : 'Ajouter le club'}
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
