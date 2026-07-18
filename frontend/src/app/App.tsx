// Shell de l'application (E00US010) : charpente minimale qui charge et se connecte.
// Les écrans métier (placement, saisie, tableaux, classement, admin) viendront comme
// features dédiées (guide §8) ; ici, le squelette + preuve de connexion bout-en-bout.

import { useEffect } from 'react'
import { TrancheVerticale } from '../features/competition/TrancheVerticale'
import { EspacePoste } from '../features/poste/EspacePoste'
import { codePosteDepuisUrl } from '../features/poste/url'
import { EtatBackend } from '../features/systeme/EtatBackend'
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
        <IndicateurConnexion />
      </header>
      <main className="app__contenu app__contenu--colonnes">
        {afficherPoste ? (
          <EspacePoste codeInitial={codePoste} />
        ) : (
          <>
            <TrancheVerticale />
            <EtatBackend />
          </>
        )}
      </main>
    </div>
  )
}
