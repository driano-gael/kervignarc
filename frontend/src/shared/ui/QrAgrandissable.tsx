// Vignette de QR **agrandissable** pour le scan — partagée (E11US008 cible, E16US015 scoreur).
//
// Le QR est de l'état **serveur** : l'appelant le charge (React Query, blob authentifié) et passe
// une **data URL** autoporteuse. Aucun objectURL à révoquer, donc pas de cycle de vie local ni de
// piège StrictMode — ici on se contente d'un `<img src>`, net à l'agrandissement (SVG vectoriel).
// ⚠️ Composant **présentational** : il ne sait pas ce que le QR encode, donc il n'a aucune règle
// d'autorisation. C'est l'écran qui monte ce composant qui répond d'être admin.

import { useEffect, useState } from 'react'

export function QrAgrandissable({
  src,
  alt,
  enErreur,
}: {
  src: string | undefined
  alt: string
  enErreur: boolean
}) {
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

  if (enErreur) return <span className="qr__indispo">QR indisponible</span>
  if (!src) return <span className="qr__attente" aria-hidden="true" />

  return (
    <>
      <button
        type="button"
        className="qr__vignette"
        onClick={() => setAgrandi(true)}
        aria-label={`Agrandir le ${alt}`}
      >
        <img src={src} alt={alt} width={72} height={72} />
      </button>
      {agrandi && (
        <div
          className="qr__overlay"
          role="dialog"
          aria-modal="true"
          aria-label={alt}
          onClick={() => setAgrandi(false)}
        >
          <img src={src} alt={alt} className="qr__grand" />
          <p className="qr__aide">Touchez l'écran pour fermer</p>
        </div>
      )}
    </>
  )
}
