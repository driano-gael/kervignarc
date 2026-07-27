// Vignette du QR de rattachement d'une cible (E11US008), **agrandissable** pour le scan.
//
// Le QR est de l'état **serveur** (image SVG chargée via React Query, en blob authentifié —
// `useQrCible`). L'`objectURL` qui l'affiche a, lui, un cycle de vie **local** (il faut le révoquer
// pour ne pas fuiter de mémoire) : on le crée/détruit ici par effet, à partir du blob mis en cache.
// Un `<img>` sur un blob SVG s'affiche et se met à l'échelle proprement (vectoriel → net une fois
// agrandi). La route est admin (le QR encode le code, secret d'usage) : cet écran l'est déjà.

import { useEffect, useMemo, useState } from 'react'

import { useQrCible } from './hooks'

export function QrCible({ tournoiId, cibleIndex }: { tournoiId: number; cibleIndex: number }) {
  const { data: blob, isError } = useQrCible(tournoiId, cibleIndex)
  const [agrandi, setAgrandi] = useState(false)

  // L'`objectURL` se **dérive** du blob (pas d'état à synchroniser dans un effet — cf. règle lint
  // `set-state-in-effect`) ; l'effet ci-dessous ne porte que sa **révocation** (nettoyage mémoire),
  // rejouée à chaque changement d'URL et au démontage.
  const url = useMemo(() => (blob ? URL.createObjectURL(blob) : null), [blob])
  useEffect(() => {
    if (!url) return
    return () => URL.revokeObjectURL(url)
  }, [url])

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
  if (!url) return <span className="qr-cible__attente" aria-hidden="true" />

  const alt = `QR de rattachement de la cible ${cibleIndex}`
  return (
    <>
      <button
        type="button"
        className="qr-cible__vignette"
        onClick={() => setAgrandi(true)}
        aria-label={`Agrandir le ${alt}`}
      >
        <img src={url} alt={alt} width={72} height={72} />
      </button>
      {agrandi && (
        <div
          className="qr-cible__overlay"
          role="dialog"
          aria-modal="true"
          aria-label={alt}
          onClick={() => setAgrandi(false)}
        >
          <img src={url} alt={alt} className="qr-cible__grand" />
          <p className="qr-cible__aide">Touchez l'écran pour fermer</p>
        </div>
      )}
    </>
  )
}
