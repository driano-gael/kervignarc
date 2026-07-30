// Shell de l'application (E00US017, ADR-0042 ; adressé en E14US003) : charpente minimale (en-tête +
// « changer de rôle » + indicateur de connexion) qui aiguille vers **le monde du rôle choisi**.
//
// Au 1ᵉʳ lancement, l'app présente un **écran de choix** à quatre portes (Tablette / Public / Scoreur
// / Admin) ; le choix est mémorisé et l'app y va **droit** ensuite.
//
// **Chaque monde a désormais son adresse** (`/public`, `/scoreur`, `/cible`, `/admin`) — routeur
// maison, cf. `routeur.ts`. L'aiguillage combine donc deux sources, l'adresse et l'état de session,
// dans la fonction pure `mondeAServir` : le verrou de poste (`D-13`) prime sur tout, l'adresse
// l'emporte ensuite sur un choix mémorisé, et la racine retombe sur `resoudreRole`. Quand le monde
// servi ne correspond pas à l'adresse, celle-ci est **corrigée en `replaceState`** — sans quoi le
// bouton « précédent » renverrait sur l'adresse que l'app vient de refuser.

import { useEffect } from 'react'
import { CoquilleAdmin } from '../features/admin/CoquilleAdmin'
import { EspacePoste } from '../features/poste/EspacePoste'
import { codePosteDepuisUrl } from '../features/poste/url'
import { AccueilPublic } from '../features/public/AccueilPublic'
import { EspaceScoreur } from '../features/scoreur-session/EspaceScoreur'
import { IndicateurConnexion } from '../shared/realtime/IndicateurConnexion'
import { useSessionAdminStore } from '../shared/stores/sessionAdminStore'
import { useSessionPosteStore } from '../shared/stores/sessionPosteStore'
import { useSessionRoleStore, type Role } from '../shared/stores/sessionRoleStore'
import { useSessionScoreurStore } from '../shared/stores/sessionScoreurStore'
import { ChangerDeRole } from './ChangerDeRole'
import { EcranAccueil } from './EcranAccueil'
import { mondeAServir, peutChangerDeRole } from './resoudreRole'
import { analyserChemin, construireChemin, roleDuMonde } from '../shared/navigation/routeur'
import { naviguer, useChemin } from '../shared/navigation/useChemin'
import './App.css'

export function App() {
  const roleChoisi = useSessionRoleStore((s) => s.role)
  const choisirRole = useSessionRoleStore((s) => s.choisir)
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

  const route = analyserChemin(useChemin())
  const { monde, corrigerUrl } = mondeAServir(route.monde, {
    roleChoisi,
    estPoste,
    codePosteUrl: codePoste !== null,
    aJetonAdmin,
    aJetonScoreur,
  })
  const role = roleDuMonde(monde)

  // L'adresse doit dire la vérité sur l'écran affiché. `replaceState` (et non `pushState`) : cette
  // correction est **subie**, pas voulue — l'empiler dans l'historique ferait boucler le bouton
  // « précédent » sur une adresse que l'app refuse.
  useEffect(() => {
    if (corrigerUrl) naviguer(construireChemin({ monde, segments: [] }), { remplacer: true })
  }, [corrigerUrl, monde])

  // Franchir une porte pose le marqueur de choix **et** change l'adresse : les deux doivent rester
  // d'accord, sinon un rechargement ramènerait à l'écran de choix.
  const choisirMonde = (choisi: Role) => {
    choisirRole(choisi)
    naviguer(construireChemin({ monde: choisi, segments: [] }))
  }

  // Échappatoire d'en-tête « Changer de rôle » : prédicat pur testé (`peutChangerDeRole`), qui garde
  // le verrou D-13 pour une vraie tablette (rattachée / arrivée QR) mais laisse réversible une tablette
  // seulement choisie au menu (cf. `resoudreRole.ts` pour le raisonnement).
  const changementPossible = peutChangerDeRole(role, estPoste, codePoste !== null)

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
          <EcranAccueil onChoisir={choisirMonde} />
        )}
      </main>
    </div>
  )
}
