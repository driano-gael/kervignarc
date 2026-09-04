// QR de rattachement d'une cible (E11US008) — le chargement ici, l'affichage en partagé.
//
// L'agrandissement, la fermeture au clavier et les classes vivent dans `QrAgrandissable`, commun
// avec le QR d'un scoreur (E16US015). La route est admin (le QR encode le code, secret d'usage) :
// cet écran l'est déjà.

import { QrAgrandissable } from '../../shared/ui/QrAgrandissable'

import { useQrCible } from './hooks'

export function QrCible({ tournoiId, cibleIndex }: { tournoiId: number; cibleIndex: number }) {
  const { data: src, isError } = useQrCible(tournoiId, cibleIndex)
  return (
    <QrAgrandissable
      src={src}
      alt={`QR de rattachement de la cible ${cibleIndex}`}
      enErreur={isError}
    />
  )
}
