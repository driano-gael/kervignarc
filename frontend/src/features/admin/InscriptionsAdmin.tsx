// La destination « Inscriptions » de l'admin : créer un archer, puis la liste en « recherche
// d'abord » (A09, E17US007). Ce conteneur lit les populations des compteurs que l'écran `Archers`
// ne peut pas lire lui-même sans dépendre de `placement` et `paiements` — cf. ses props.

import { useState } from 'react'
import { Archers } from '../archers/Archers'
import { useArchers } from '../archers/hooks'
import { NouvelArcher } from '../archers/NouvelArcher'
import { ImportInscrits } from '../import-inscrits/ImportInscrits'
import { useArchersNonRegles } from '../paiements/hooks'
import { usePlansDuTournoi } from '../placement/hooks'
import { archersNonPlaces } from '../placement/nonPlaces'

export function InscriptionsAdmin({
  tournoiId,
  ouvrir,
  onOuvrir,
}: {
  tournoiId: number
  ouvrir: number | null
  onOuvrir: (id: number | null) => void
}) {
  const archers = useArchers(tournoiId)
  const plans = usePlansDuTournoi(tournoiId)
  const nonPlaces =
    archers.data === undefined
      ? null
      : archersNonPlaces(
          archers.data.map((a) => a.id),
          plans,
        )
  const nonRegles = useArchersNonRegles(tournoiId)
  const [importOuvert, setImportOuvert] = useState(false)
  return (
    <>
      <NouvelArcher tournoiId={tournoiId} />
      <button
        type="button"
        className="bouton--discret"
        aria-expanded={importOuvert}
        onClick={() => setImportOuvert((ouvert) => !ouvert)}
      >
        {importOuvert ? "Fermer l'import" : 'Importer une liste'}
      </button>
      {importOuvert && <ImportInscrits tournoiId={tournoiId} />}
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
