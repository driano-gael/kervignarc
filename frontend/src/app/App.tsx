// Shell de l'application (E00US010) : charpente minimale qui charge et se connecte.
// Les écrans métier (placement, saisie, tableaux, classement, admin) viendront comme
// features dédiées (guide §8) ; ici, le squelette + preuve de connexion bout-en-bout.

import { TrancheVerticale } from '../features/competition/TrancheVerticale'
import { EtatBackend } from '../features/systeme/EtatBackend'
import { IndicateurConnexion } from '../shared/realtime/IndicateurConnexion'
import './App.css'

export function App() {
  return (
    <div className="app">
      <header className="app__entete">
        <h1 className="app__titre">Kervignarc</h1>
        <IndicateurConnexion />
      </header>
      <main className="app__contenu app__contenu--colonnes">
        <TrancheVerticale />
        <EtatBackend />
      </main>
    </div>
  )
}
