// Shell de l'application (E00US010) : charpente minimale qui charge et se connecte.
// Les écrans métier (placement, saisie, tableaux, classement, admin) viendront comme
// features dédiées (guide §8) ; ici, le squelette + preuve de connexion bout-en-bout.

import { TrancheVerticale } from '../features/competition/TrancheVerticale'
import { EspacePoste } from '../features/poste/EspacePoste'
import { codePosteDepuisUrl } from '../features/poste/url'
import { EtatBackend } from '../features/systeme/EtatBackend'
import { IndicateurConnexion } from '../shared/realtime/IndicateurConnexion'
import { useSessionPosteStore } from '../shared/stores/sessionPosteStore'
import './App.css'

export function App() {
  // Une tablette **rattachée** (jeton persisté) ou arrivée par le QR de sa cible (`?poste=<code>`)
  // ouvre directement l'écran de poste — elle ne voit pas l'admin (D-13). Sinon, l'app normale.
  const jetonPoste = useSessionPosteStore((s) => s.jeton)
  const codePoste = codePosteDepuisUrl()
  const estPoste = jetonPoste !== null || codePoste !== null

  return (
    <div className="app">
      <header className="app__entete">
        <h1 className="app__titre">Kervignarc</h1>
        <IndicateurConnexion />
      </header>
      <main className="app__contenu app__contenu--colonnes">
        {estPoste ? (
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
