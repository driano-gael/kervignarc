// Complétude **administrative** (E16US003) — la moitié hors-sportive, rendue sur l'axe **gestion**.
//
// A14 a refusé l'écran unique : *« je n'aime pas le mélange entre le déroulé et la gestion
// administrative »*. Les deux listes voyagent dans **une seule réponse** (`sportif` /
// `hors_sportif`, séparées au domaine depuis E12US005) : c'est la **destination** qui change, pas
// le calcul. **Sur l'écran Paiements plutôt qu'une destination neuve** : `hors_sportif` ne porte
// qu'une ligne — une destination dédiée ne se justifiera qu'avec plusieurs sujets. Cette ligne
// compte des **archers réglés**, pas des montants.

import { texteErreur } from '../../shared/ui/texteErreur'
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
        Complétude administrative injoignable — {texteErreur(completude.error)}
      </p>
    )
  }
  if (!completude.data) return null

  return (
    <SectionCompletude
      titre="Complétude administrative"
      lignes={completude.data.hors_sportif}
      niveau={4}
    />
  )
}
