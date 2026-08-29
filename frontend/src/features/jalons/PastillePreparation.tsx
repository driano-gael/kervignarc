// La pastille de préparation d'une ligne de la liste des tournois (E16US010).
//
// « Sur cette liste laisse une pastille d'alerte si tout n'est pas complet ; alerte forte si
// impossible de lancer en l'état » (A02). Elle ne recalcule rien : le niveau vient du jalon
// « prêt à démarrer » (ADR-0096), qui est la seule source de ce que la préparation vaut.

import type { ApercuJalon } from './api'
import { pastille } from './presentation'

export function PastillePreparation({ apercu }: { apercu: ApercuJalon | undefined }) {
  // `undefined` = aperçu pas encore chargé. Ne rien rendre plutôt qu'une pastille neutre : un
  // point qui apparaît puis change de sens se lit comme un incident.
  if (apercu === undefined) return null
  const marque = pastille(apercu.niveau)
  if (marque === null) return null

  return (
    <span
      className={`badge-preparation badge-preparation--${marque.fort ? 'alerte' : 'avertissement'}`}
      title={apercu.resume ?? undefined}
    >
      {marque.libelle}
      {/* La cause chiffrée est dans le `title` pour la souris ; le lecteur d'écran, lui, n'y a pas
          accès de façon fiable — d'où sa reprise en clair, hors flux visuel. */}
      {apercu.resume !== null && <span className="sr-only"> — {apercu.resume}</span>}
    </span>
  )
}
