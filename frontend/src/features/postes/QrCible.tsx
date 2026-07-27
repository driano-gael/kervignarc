// Vignette du QR de rattachement d'une cible (E11US008), **agrandissable** pour le scan.
//
// Le QR est de l'état **serveur** : image SVG chargée via React Query en blob authentifié, puis
// exposée en **data URL** autoporteuse (`useQrCible` → `getQrCible`). Aucun objectURL à révoquer,
// donc pas de cycle de vie local ni de piège StrictMode — le composant se contente d'un `<img
// src>`. Un `<img>` sur un SVG s'affiche et se met à l'échelle proprement (vectoriel → net une fois
// agrandi). La route est admin (le QR encode le code, secret d'usage) : cet écran l'est déjà.

import { useEffect, useState } from 'react'

import { useQrCible } from './hooks'

export function QrCible({ tournoiId, cibleIndex }: { tournoiId: number; cibleIndex: number }) {
  const { data: src, isError } = useQrCible(tournoiId, cibleIndex)
  const [agrandi, setAgrandi] = useState(false)

  // Fermeture au clavier (Échap) pendant l'agrandissement : le vecteur tactile reste le clic sur
  // le fond, mais un dialogue doit rester pilotable au clavier (accessibilité).
  useEffect(() => {
    if (!agrandi) return
    const surTouche = (evenement: KeyboardEvent) => {
      if (evenement.key === 'Escape') setAgrandi(false)
    }
    window.addEventListener('keydown', surTouche)
    return () => window.removeEventListener('keydown', surTouche)
  }, [agrandi])

  if (isError) return <span className="qr-cible__indispo">QR indisponible</span>
  if (!src) return <span className="qr-cible__attente" aria-hidden="true" />

  const alt = `QR de rattachement de la cible ${cibleIndex}`
  return (
    <>
      <button
        type="button"
        className="qr-cible__vignette"
        onClick={() => setAgrandi(true)}
        aria-label={`Agrandir le ${alt}`}
      >
        <img src={src} alt={alt} width={72} height={72} />
      </button>
      {agrandi && (
        <div
          className="qr-cible__overlay"
          role="dialog"
          aria-modal="true"
          aria-label={alt}
          onClick={() => setAgrandi(false)}
        >
          <img src={src} alt={alt} className="qr-cible__grand" />
          <p className="qr-cible__aide">Touchez l'écran pour fermer</p>
        </div>
      )}
    </>
  )
}
