// La destination « Inscriptions » de l'admin : créer un archer, puis la liste en « recherche
// d'abord » (A09, E17US007). Ce conteneur lit les populations des compteurs que l'écran `Archers`
// ne peut pas lire lui-même sans dépendre de `placement` et `paiements` — cf. ses props.

import { Archers } from '../archers/Archers'
import { NouvelArcher } from '../archers/NouvelArcher'
import { useArchersNonRegles } from '../paiements/hooks'
import { useArchersEnReserve } from '../placement/hooks'

export function InscriptionsAdmin({
  tournoiId,
  ouvrir,
  onOuvrir,
}: {
  tournoiId: number
  ouvrir: number | null
  onOuvrir: (id: number | null) => void
}) {
  const nonPlaces = useArchersEnReserve(tournoiId)
  const nonRegles = useArchersNonRegles(tournoiId)
  return (
    <>
      <NouvelArcher tournoiId={tournoiId} />
      <Archers
        tournoiId={tournoiId}
        ouvrir={ouvrir}
        onOuvrir={onOuvrir}
        nonPlaces={nonPlaces}
        nonRegles={nonRegles}
      />
    </>
  )
}
