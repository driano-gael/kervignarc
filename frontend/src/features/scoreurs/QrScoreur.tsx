// QR de session d'un scoreur (E16US015) — le chargement ici, l'affichage en partagé.
//
// ⚠️ **Ce composant n'est monté que lorsque l'admin a demandé CE scoreur**, un seul à la fois : le
// QR encode un code personnel, et un écran qui les afficherait tous se photographie d'un cliché.
// Le désarmement effectif de l'appel réseau est dans `useQrScoreur` (`enabled`), pas ici — monter
// le composant suffit donc à déclencher la lecture, et c'est voulu.

import { QrAgrandissable } from '../../shared/ui/QrAgrandissable'

import { useQrScoreur } from './hooks'

export function QrScoreur({
  tournoiId,
  scoreurId,
  nom,
}: {
  tournoiId: number
  scoreurId: number
  nom: string
}) {
  const { data: src, isError } = useQrScoreur(tournoiId, scoreurId, true)
  return <QrAgrandissable src={src} alt={`QR de session de ${nom}`} enErreur={isError} />
}
