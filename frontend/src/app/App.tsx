// Shell de l'application : charpente minimale (en-tête + indicateur de connexion) qui aiguille vers
// l'écran de poste (tablette rattachée) ou l'appli d'organisation (coquille admin + consultation
// publique, E00US015).

import { useEffect } from 'react'
import { CoquilleAdmin } from '../features/admin/CoquilleAdmin'
import { EspacePoste } from '../features/poste/EspacePoste'
import { codePosteDepuisUrl } from '../features/poste/url'
import { IndicateurConnexion } from '../shared/realtime/IndicateurConnexion'
import { useSessionPosteStore } from '../shared/stores/sessionPosteStore'
import './App.css'

export function App() {
  // Une tablette qui **est un poste** (marqueur persistant, posé au rattachement ou à l'arrivée par
  // le QR de sa cible `?poste=<code>`) ouvre directement l'écran de poste — elle ne voit jamais
  // l'admin (D-13), et une session révoquée la laisse sur le rattachement, pas sur l'admin. Elle ne
  // rebascule sur l'app normale qu'au **détachement explicite**. Sinon, l'app normale.
  const estPoste = useSessionPosteStore((s) => s.estPoste)
  const entrerModePoste = useSessionPosteStore((s) => s.entrerModePoste)
  const codePoste = codePosteDepuisUrl()

  useEffect(() => {
    if (codePoste !== null && !estPoste) entrerModePoste()
  }, [codePoste, estPoste, entrerModePoste])

  const afficherPoste = estPoste || codePoste !== null

  return (
    <div className="app">
      <header className="app__entete">
        <h1 className="app__titre">Kervignarc</h1>
        {/* L'état de connexion reste porté par cette **pastille** permanente (E00US015 a retiré
            l'écran de diagnostic redondant `systeme/EtatBackend`) — un voyant, pas une destination. */}
        <IndicateurConnexion />
      </header>
      <main className="app__contenu">
        {afficherPoste ? <EspacePoste codeInitial={codePoste} /> : <CoquilleAdmin />}
      </main>
    </div>
  )
}
