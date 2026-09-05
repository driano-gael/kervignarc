// QR de session d'un scoreur (E16US015) — le chargement ici, l'affichage en partagé.
//
// ⚠️ **Le montage EST la garde** : ce composant n'existe que lorsque l'admin a demandé CE scoreur,
// un seul à la fois (`Scoreurs.tsx`, état `qrOuvert`). Le monter suffit à déclencher la lecture —
// donc le monter sans condition demanderait les codes de tous les scoreurs d'un coup, ce que
// l'arbitrage du 04/09/2026 ferme (ADR-0105).

import { QrAgrandissable } from '../../shared/ui/QrAgrandissable'

import { useQrScoreur } from './hooks'

export function QrScoreur({
  tournoiId,
  scoreurId,
  code,
  nom,
}: {
  tournoiId: number
  scoreurId: number
  code: string
  nom: string
}) {
  const { data: src, isError } = useQrScoreur(tournoiId, scoreurId, code)
  return <QrAgrandissable src={src} alt={`QR de session de ${nom}`} enErreur={isError} />
}
