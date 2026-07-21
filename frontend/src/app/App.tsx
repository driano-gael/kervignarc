// Shell de l'application (E00US017, ADR-0042) : charpente minimale (en-tête + « changer de rôle » +
// indicateur de connexion) qui aiguille vers **le monde du rôle choisi**.
//
// Au 1ᵉʳ lancement, l'app présente un **écran de choix** à quatre portes (Tablette / Public / Scoreur
// / Admin) ; le choix est mémorisé et l'app y va **droit** ensuite. Le rôle **effectif** est résolu
// par `resoudreRole` (fonction pure testée) : une **session en cours prime** sur le choix, pour qu'un
// rechargement ne renvoie jamais sur l'écran de choix (résilience jour J). Arriver par le QR d'une
// cible (`?poste=<code>`) force le rôle tablette (verrou physique D-13).

import { useEffect } from 'react'
import { CoquilleAdmin } from '../features/admin/CoquilleAdmin'
import { EspacePoste } from '../features/poste/EspacePoste'
import { codePosteDepuisUrl } from '../features/poste/url'
import { AccueilPublic } from '../features/public/AccueilPublic'
import { EspaceScoreur } from '../features/scoreur-session/EspaceScoreur'
import { IndicateurConnexion } from '../shared/realtime/IndicateurConnexion'
import { useSessionAdminStore } from '../shared/stores/sessionAdminStore'
import { useSessionPosteStore } from '../shared/stores/sessionPosteStore'
import { useSessionRoleStore } from '../shared/stores/sessionRoleStore'
import { useSessionScoreurStore } from '../shared/stores/sessionScoreurStore'
import { ChangerDeRole } from './ChangerDeRole'
import { EcranAccueil } from './EcranAccueil'
import { resoudreRole } from './resoudreRole'
import './App.css'

export function App() {
  const roleChoisi = useSessionRoleStore((s) => s.role)
  const estPoste = useSessionPosteStore((s) => s.estPoste)
  const entrerModePoste = useSessionPosteStore((s) => s.entrerModePoste)
  const aJetonAdmin = useSessionAdminStore((s) => s.jeton) !== null
  const aJetonScoreur = useSessionScoreurStore((s) => s.jeton) !== null
  const codePoste = codePosteDepuisUrl()

  // Arriver par le QR de sa cible marque d'emblée le navigateur comme poste (avant même le
  // rattachement) : le rôle tablette est alors verrouillé et l'écran de choix sauté.
  useEffect(() => {
    if (codePoste !== null && !estPoste) entrerModePoste()
  }, [codePoste, estPoste, entrerModePoste])

  const role = resoudreRole({
    roleChoisi,
    estPoste,
    codePosteUrl: codePoste !== null,
    aJetonAdmin,
    aJetonScoreur,
  })

  // Échappatoire d'en-tête « Changer de rôle ». Le verrou D-13 (pas d'échappatoire) ne vaut que pour
  // une **vraie** tablette — poste rattaché (`estPoste`) ou arrivée par QR (`codePoste`) : contrôle
  // d'accès physique. Une tablette **seulement choisie au menu** (marqueur `roleChoisi='tablette'`,
  // pas encore rattachée) reste réversible : sans ça, un mauvais tap sur « Tablette » piège
  // l'utilisateur sur le rattachement, sans « Détacher » (qui n'existe qu'une fois rattaché) ni
  // moyen de revenir au choix (correctif de revue adversariale E00US017). L'écran de choix
  // (role === null) n'a pas d'échappatoire non plus.
  const tabletteVerrouillee = role === 'tablette' && (estPoste || codePoste !== null)
  const changementPossible = role !== null && !tabletteVerrouillee

  return (
    <div className="app">
      <header className="app__entete">
        <h1 className="app__titre">Kervignarc</h1>
        <div className="app__actions">
          {changementPossible && <ChangerDeRole />}
          {/* Voyant de connexion permanent — un état, pas une destination. */}
          <IndicateurConnexion />
        </div>
      </header>
      <main className="app__contenu">
        {role === 'tablette' ? (
          <EspacePoste codeInitial={codePoste} />
        ) : role === 'public' ? (
          <AccueilPublic />
        ) : role === 'scoreur' ? (
          <EspaceScoreur />
        ) : role === 'admin' ? (
          <CoquilleAdmin />
        ) : (
          <EcranAccueil />
        )}
      </main>
    </div>
  )
}
