// Espace scoreur (E10US003) — l'entrée du scoreur, ouverte à tous (c'est l'authentification).
//
// Le scoreur ouvre l'app sur son propre téléphone et tape **son code** (mode d'identité « la
// personne », D-13). Une session nominative s'ouvre alors, persistée localement pour survivre à la
// fermeture de l'onglet le temps de la journée. Il est **itinérant** : sa session n'est rattachée à
// aucune cible (D-12) — il pourra valider n'importe laquelle. La **surface de validation** (voir les
// cibles, valider) relève de la saisie (E04US002) : ici, on ouvre et on ferme la session.

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import {
  type ScoreurConnecte,
  useSessionScoreurStore,
} from '../../shared/stores/sessionScoreurStore'
import { useConnexionScoreur, useDeconnexionScoreur } from './hooks'

export function EspaceScoreur() {
  const scoreur = useSessionScoreurStore((s) => s.scoreur)

  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">Espace scoreur</h2>
      {scoreur ? <SessionOuverte scoreur={scoreur} /> : <FormulaireCode />}
    </section>
  )
}

function FormulaireCode() {
  const [code, setCode] = useState('')
  const connexion = useConnexionScoreur()

  const entreeValide = code.trim() !== ''

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!entreeValide) return
    connexion.mutate(code)
  }

  return (
    <div>
      <p className="carte__etat">
        Entrez le code qui vous a été remis pour valider les scores de ce tournoi.
      </p>
      <form className="formulaire" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Votre code"
          aria-label="Code du scoreur"
          autoComplete="one-time-code"
          autoCapitalize="characters"
        />
        <button type="submit" disabled={connexion.isPending || !entreeValide}>
          Ouvrir ma session
        </button>
      </form>
      <MessageErreur erreur={connexion.error} />
    </div>
  )
}

function SessionOuverte({ scoreur }: { scoreur: ScoreurConnecte }) {
  const deconnexion = useDeconnexionScoreur()

  return (
    <div>
      <p className="carte__etat">
        Session ouverte — <strong>{scoreur.nom}</strong>. La validation des scores depuis cet
        appareil arrivera avec la saisie (à venir).
      </p>
      <button
        type="button"
        className="lien"
        disabled={deconnexion.isPending}
        onClick={() => deconnexion.mutate()}
      >
        Fermer ma session
      </button>
      <MessageErreur erreur={deconnexion.error} />
    </div>
  )
}
