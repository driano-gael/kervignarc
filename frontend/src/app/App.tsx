// Shell de l'application (E00US017, ADR-0042 ; adressé en E14US003) : charpente minimale qui
// aiguille vers **le monde du rôle choisi**.
//
// Au 1ᵉʳ lancement, un **écran de choix** à cinq portes, mémorisé ensuite. Cinq portes pour quatre
// mondes : `cible` et `salle` sont deux entrées d'un même monde. L'aiguillage combine adresse et
// état de session dans `mondeAServir` — le verrou de poste (`D-13`) prime. ⚠️ Quand le monde servi
// ne correspond pas à l'adresse, celle-ci est **corrigée en `replaceState`** : sinon « précédent »
// renverrait sur l'adresse que l'app vient de refuser.

import { useEffect, useState } from 'react'
import { CoquilleAdmin } from '../features/admin/CoquilleAdmin'
import { EspacePoste } from '../features/poste/EspacePoste'
import { codePosteDepuisUrl } from '../features/poste/url'
import { codeScoreurDepuisUrl, oublierCodeScoreurUrl } from '../features/scoreur-session/url'
import { AccueilPublic } from '../features/public/AccueilPublic'
import { EspaceScoreur } from '../features/scoreur-session/EspaceScoreur'
import { IndicateurConnexion } from '../shared/realtime/IndicateurConnexion'
import { useSessionAdminStore } from '../shared/stores/sessionAdminStore'
import { useSessionPosteStore } from '../shared/stores/sessionPosteStore'
import { useSessionRoleStore } from '../shared/stores/sessionRoleStore'
import { useSessionScoreurStore } from '../shared/stores/sessionScoreurStore'
import { ChangerDeRole } from '../shared/ui/ChangerDeRole'
import { EcranAccueil } from './EcranAccueil'
import { mondeAServir, peutChangerDeRole } from './resoudreRole'
import {
  analyserChemin,
  cheminDePorte,
  construireChemin,
  porteDuChemin,
  roleDeLaPorte,
  roleDuMonde,
  type Porte,
} from '../shared/navigation/routeur'
import { naviguer, useChemin } from '../shared/navigation/useChemin'
import './App.css'
// Après `App.css`, et jamais avant : les feuilles de feature complètent le socle du shell, donc
// elles doivent gagner à spécificité égale. Cf. l'en-tête de `features.css`.
import './features.css'

export function App() {
  const roleChoisi = useSessionRoleStore((s) => s.role)
  const choisirRole = useSessionRoleStore((s) => s.choisir)
  const estPoste = useSessionPosteStore((s) => s.estPoste)
  const posteEstEcran = useSessionPosteStore((s) => s.poste?.type === 'ecran')
  const entrerModePoste = useSessionPosteStore((s) => s.entrerModePoste)
  const aJetonAdmin = useSessionAdminStore((s) => s.jeton) !== null
  const aJetonScoreur = useSessionScoreurStore((s) => s.jeton) !== null
  const codePoste = codePosteDepuisUrl()
  // Le code d'arrivée d'un scoreur est lu **une fois** puis effacé de l'adresse, ⚠️ **ici et non
  // dans `EspaceScoreur`** : sur une tablette déjà rattachée, le verrou de poste (`D-13`) sert le
  // monde `tablette` et cet espace n'est jamais monté — le code personnel resterait affiché dans la
  // barre d'adresse d'un appareil partagé allumé toute la journée. `naviguer` ne nettoie pas non
  // plus : il **conserve** query et fragment, pour le `?poste=` du QR de cible.
  const [codeScoreur] = useState(() => codeScoreurDepuisUrl())
  useEffect(() => {
    if (codeScoreur !== null) oublierCodeScoreurUrl()
  }, [codeScoreur])

  // Arriver par le QR de sa cible marque d'emblée le navigateur comme poste (avant même le
  // rattachement) : le rôle tablette est alors verrouillé et l'écran de choix sauté.
  useEffect(() => {
    if (codePoste !== null && !estPoste) entrerModePoste()
  }, [codePoste, estPoste, entrerModePoste])

  const chemin = useChemin()
  const route = analyserChemin(chemin)
  // La porte **nommée par l'adresse** : `/salle` et `/cible` mènent au même monde, mais pas au même
  // discours. On la lit ici plutôt que de la mémoriser — l'adresse survit déjà au rechargement, un
  // état de plus n'aurait fait que diverger d'elle (cf. `porteDuChemin`).
  const porteUrl = porteDuChemin(chemin)
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

  // Franchir une porte pose le marqueur de **rôle** (deux portes peuvent partager un rôle) et
  // navigue vers **l'adresse de la porte**, qui est plus précise que celle du monde : c'est elle qui
  // fera parler juste l'écran de rattachement, et qui restera affichée sur une machine allumée pour
  // la journée.
  const choisirMonde = (porte: Porte) => {
    choisirRole(roleDeLaPorte(porte))
    naviguer(cheminDePorte(porte))
  }

  // Échappatoire d'en-tête « Changer de rôle » : prédicat pur testé (`peutChangerDeRole`), qui garde
  // le verrou D-13 pour une vraie tablette (rattachée / arrivée QR) mais laisse réversible une tablette
  // seulement choisie au menu (cf. `resoudreRole.ts` pour le raisonnement).
  const changementPossible = peutChangerDeRole(role, estPoste, codePoste !== null)

  // **La surface annonce sa nature au CSS** (A02, 04/08/2026). Le shell imposait une seule largeur
  // — 960 px — à cinq surfaces aux contraintes **opposées** : PC d'organisation, téléphone,
  // tablette, vidéoprojecteur. C'est ce qui rendait l'admin « tassé » *et* ce qui reléguait l'écran
  // de salle dans une colonne de 960 px au milieu d'un mur de 1920. `data-monde` plutôt qu'une
  // classe : c'est un **état de la surface**, et il pilote des jetons que chaque règle consomme. ⚠️
  // L'écran de salle est distingué **par sa session, pas par son adresse** — le monde est
  // `tablette` dans les deux cas, et un écran atteint par QR n'a pas d'adresse `/salle`.
  const surface = posteEstEcran ? 'salle' : monde

  return (
    <div className="app" data-monde={surface}>
      {/* En-tête masqué sur un écran projeté : il n'y a personne pour cliquer, et le bandeau de la
          salle porte déjà le lieu et l'état hors ligne. */}
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
          <EspacePoste
            codeInitial={codePoste}
            vocation={porteUrl === 'salle' ? 'salle' : 'cible'}
          />
        ) : role === 'public' ? (
          <AccueilPublic />
        ) : role === 'scoreur' ? (
          <EspaceScoreur codeUrl={codeScoreur} />
        ) : role === 'admin' ? (
          <CoquilleAdmin />
        ) : (
          <EcranAccueil onChoisir={choisirMonde} />
        )}
      </main>
    </div>
  )
}
