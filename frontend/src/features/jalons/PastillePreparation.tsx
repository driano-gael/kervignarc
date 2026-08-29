// La pastille de préparation d'une ligne de la liste des tournois (E16US010).
//
// « Sur cette liste laisse une pastille d'alerte si tout n'est pas complet ; alerte forte si
// impossible de lancer en l'état » (A02). Elle ne recalcule rien : le niveau vient du jalon
// « prêt à démarrer » (ADR-0096), qui est la seule source de ce que la préparation vaut.

import { useState } from 'react'
import type { ApercuJalon } from './api'
import { pastille } from './presentation'

export function PastillePreparation({ apercu }: { apercu: ApercuJalon | undefined }) {
  const [causeVisible, setCauseVisible] = useState(false)
  // `undefined` = aperçu pas encore chargé. Ne rien rendre plutôt qu'une pastille neutre : un
  // point qui apparaît puis change de sens se lit comme un incident.
  if (apercu === undefined) return null
  const marque = pastille(apercu.niveau)
  if (marque === null) return null

  const classe = `badge-preparation badge-preparation--${marque.fort ? 'alerte' : 'avertissement'}`
  // ⚠️ **Un bouton, pas un `title` seul.** Le parc est fait de ~30 tablettes (règle 10) : au doigt,
  // il n'y a ni survol ni lecteur d'écran, donc la cause chiffrée qu'exige `D-16` n'existait pas —
  // la pastille redevenait le « clic de plus » que `D-16` refuse. Le `title` reste pour la souris.
  if (apercu.resume === null) return <span className={classe}>{marque.libelle}</span>
  return (
    <>
      <button
        type="button"
        className={classe}
        title={apercu.resume}
        aria-expanded={causeVisible}
        onClick={() => setCauseVisible((visible) => !visible)}
      >
        {marque.libelle}
      </button>
      {causeVisible && <span className="badge-preparation__cause">{apercu.resume}</span>}
    </>
  )
}
