// Référentiel des clubs (E02US001) — réservé à l'admin (monté sous `estAdmin`).
//
// Tableau + création + renommage depuis la ligne + suppression à confirmation (E00US016). Le référentiel est **global** : aucun
// `tournoiId` en entrée, les clubs se réutilisent d'une compétition à l'autre. L'unicité du nom
// (casse **et accents** repliés) est vérifiée côté serveur : un doublon rend un 409, affiché tel
// quel — le message du serveur nomme le club déjà présent.

import { useState } from 'react'
import { useOuvertureParAdresse } from '../../shared/navigation/useOuvertureParAdresse'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import type { Club, NouveauClub } from './api'
import { useClubs, useCreerClub, useModifierClub, useSupprimerClub } from './hooks'

export function Clubs({
  ouvrir,
  onOuvrir,
}: {
  // ⚠️ **Requis** : voir `Archers` — optionnels, un site de montage pouvait les oublier en silence.
  ouvrir: number | null
  onOuvrir: (id: number | null) => void
}) {
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
        <div className="table-defilement">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Nom</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            {clubs.data.map((club) => (
              <LigneClub key={club.id} club={club} ouvrir={ouvrir} onOuvrir={onOuvrir} />
            ))}
          </table>
        </div>
      )}
    </section>
  )
}

// Nom, actions — la largeur d'une ligne de détail ou du formulaire de renommage.
const COLONNES = 2

function LigneClub({
  club,
  ouvrir,
  onOuvrir,
}: {
  club: Club
  ouvrir: number | null
  onOuvrir: (id: number | null) => void
}) {
  const [edition, setEdition] = useOuvertureParAdresse(club.id, ouvrir, onOuvrir)
  const [confirmationSuppression, setConfirmationSuppression] = useState(false)
  const supprimer = useSupprimerClub()

  // Un `<tbody>` par club : la ligne et son erreur de suppression se tiennent ensemble.
  if (edition) {
    return (
      <tbody>
        <tr>
          <td colSpan={COLONNES}>
            <FormulaireClub club={club} onTermine={() => setEdition(false)} />
          </td>
        </tr>
      </tbody>
    )
  }

  return (
    <tbody>
      <tr>
        <td className="club__nom">{club.nom}</td>
        <td>
          {/* Le nom accessible nomme le club : vingt « Supprimer » identiques au lecteur d'écran. */}
          <span className="club__actions">
            <button
              type="button"
              className="bouton--discret"
              aria-label={`Renommer ${club.nom}`}
              onClick={() => setEdition(true)}
            >
              Renommer
            </button>
            {confirmationSuppression ? (
              <>
                <button
                  type="button"
                  className="bouton--danger"
                  disabled={supprimer.isPending}
                  aria-label={`Confirmer la suppression de ${club.nom}`}
                  onClick={() => supprimer.mutate(club.id)}
                >
                  Confirmer la suppression
                </button>
                <button
                  type="button"
                  className="bouton--discret"
                  aria-label={`Annuler la suppression de ${club.nom}`}
                  onClick={() => setConfirmationSuppression(false)}
                >
                  Annuler
                </button>
              </>
            ) : (
              <button
                type="button"
                className="bouton--danger"
                aria-label={`Supprimer ${club.nom}`}
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
