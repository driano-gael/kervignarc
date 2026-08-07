// Complétude **administrative** (E16US003) — la moitié hors-sportive de `GET /completude`, rendue
// sur l'axe **gestion**, là où l'organisateur la traite.
//
// Pourquoi ce composant existe : le questionnaire A14 a refusé l'écran de complétude parce qu'il
// mélangeait les deux mondes — *« je n'aime pas le mélange entre le déroulé et la gestion
// administrative ; complétude en déroulé n'est pas complétude administrative, en déroulé on est
// centré sur l'événement »*. Les deux listes voyagent toujours dans **une seule réponse** serveur
// (`sportif` / `hors_sportif`, déjà séparées côté domaine depuis E12US005) : rien n'est recalculé
// ici, c'est la **destination** qui change, pas le calcul.
//
// **Pourquoi sur l'écran Paiements et non sur une destination neuve** : `hors_sportif` ne porte
// aujourd'hui qu'**une** ligne, « Paiements » (`domain/completude.py`). Lui donner une destination
// propre aurait posé, dans l'axe gestion, un écran d'une seule ligne juste au-dessus de l'écran qui
// traite exactement ce sujet. Le CA demande « deux destinations » : `paiements` **est** une
// destination de l'axe gestion. Une destination dédiée ne se justifierait que le jour où le
// hors-sportif porte plusieurs sujets — on ne fabrique pas l'ossature d'une évolution supposée.
//
// Ce que cette ligne dit et que le total en euros ne dit pas : elle compte des **archers réglés**,
// pas des montants. « 113/120 » répond à « combien de personnes reste-t-il à encaisser », question
// d'accueil, quand « reste 56 € » répond à « combien manque-t-il en caisse ». Les deux se lisent.

import { useCompletude } from './hooks'
import { SectionCompletude } from './SectionCompletude'

export function CompletudeAdministrative({ tournoiId }: { tournoiId: number }) {
  const completude = useCompletude(tournoiId)

  // Discret par construction : cet encart est un **appoint** sur l'écran des paiements, pas son
  // sujet. En chargement il ne prend pas de place (le tableau, lui, affiche déjà « Chargement… ») ;
  // en erreur il le dit sans masquer le reste de l'écran, qui reste utilisable.
  if (completude.isError) {
    return (
      <p className="carte__etat carte__etat--erreur" role="alert">
        Complétude administrative injoignable — {completude.error.message}
      </p>
    )
  }
  if (!completude.data) return null

  return (
    <SectionCompletude titre="Complétude administrative" lignes={completude.data.hors_sportif} />
  )
}
