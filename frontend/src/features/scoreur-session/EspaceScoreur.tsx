// Espace scoreur (E10US003) — l'entrée du scoreur, ouverte à tous (c'est l'authentification).
//
// Le scoreur ouvre l'app sur son propre téléphone et tape **son code** (mode d'identité « la
// personne », D-13). Une session nominative s'ouvre alors, persistée localement pour survivre à la
// fermeture de l'onglet le temps de la journée. Il est **itinérant** : sa session n'est rattachée à
// aucune cible (D-12) — il pourra valider n'importe laquelle. La **surface de validation** (voir les
// cibles, valider) relève de la saisie (E04US002) : ici, on ouvre et on ferme la session.

import { useEffect, useRef, useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import {
  type ScoreurConnecte,
  useSessionScoreurStore,
} from '../../shared/stores/sessionScoreurStore'
import { SaisieDuels } from '../saisie-duels/SaisieDuels'
import { SaisiePoules } from '../poules/SaisiePoules'
import { SaisieBigShootOff } from '../big-shoot-off/SaisieBigShootOff'
import { SaisieColline } from '../colline/SaisieColline'
import { SaisieSuisse } from '../suisse/SaisieSuisse'
import { ChoixCreneau } from '../departs/ChoixCreneau'
import { useCreneauDesDuels } from '../departs/hooks'
import { PanneauForfaitsQualif } from '../forfaits/PanneauForfaitsQualif'
import { useConnexionScoreur, useDeconnexionScoreur } from './hooks'
import { codeScoreurDepuisUrl, oublierCodeScoreurUrl } from './url'

export function EspaceScoreur() {
  const scoreur = useSessionScoreurStore((s) => s.scoreur)
  // Arrivée par le QR (E16US015) : le code est lu **une fois**, au premier rendu, puis effacé de
  // l'adresse — quel que soit l'état de la session. ⚠️ L'effacement est ici et non dans le
  // formulaire : un scoreur déjà connecté qui rescanne son QR ne monte pas le formulaire, et son
  // code personnel resterait dans la barre d'adresse et l'historique du téléphone.
  const [codeUrl] = useState(() => codeScoreurDepuisUrl())
  useEffect(() => {
    if (codeUrl !== null) oublierCodeScoreurUrl()
  }, [codeUrl])

  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">Espace scoreur</h2>
      {scoreur ? <SessionOuverte scoreur={scoreur} /> : <FormulaireCode codeUrl={codeUrl} />}
    </section>
  )
}

function FormulaireCode({ codeUrl }: { codeUrl: string | null }) {
  // Arrivée par le QR (E16US015) : le champ est prérempli, et la session s'ouvre sans geste. Le
  // champ garde le code même si l'appel échoue — le scoreur corrige au lieu de repartir de zéro.
  const [code, setCode] = useState(codeUrl ?? '')
  const connexion = useConnexionScoreur()
  // ⚠️ Garde de **tentative unique**. Sans elle, StrictMode (double montage en dev) rejouerait la
  // connexion, et tout re-rendu du formulaire aussi — le champ resterait prérempli tant que l'appel
  // n'a pas abouti. Un `ref` et non un `state` : ce drapeau ne doit provoquer aucun rendu.
  const tentee = useRef(false)

  const { mutate } = connexion
  useEffect(() => {
    if (tentee.current || codeUrl === null || codeUrl.trim() === '') return
    tentee.current = true
    mutate(codeUrl)
  }, [codeUrl, mutate])

  const entreeValide = code.trim() !== ''

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!entreeValide) return
    connexion.mutate(code)
  }

  return (
    <div>
      <p className="carte__etat">
        Entrez le code qui vous a été remis pour valider les scores de ce tournoi.
      </p>
      <form className="formulaire" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Votre code"
          aria-label="Code du scoreur"
          autoComplete="one-time-code"
          autoCapitalize="characters"
        />
        <button type="submit" disabled={connexion.isPending || !entreeValide}>
          Ouvrir ma session
        </button>
      </form>
      <MessageErreur erreur={connexion.error} />
    </div>
  )
}

function SessionOuverte({ scoreur }: { scoreur: ScoreurConnecte }) {
  const deconnexion = useDeconnexionScoreur()
  // ✅ **`DETTE-056` refermée ici (E05US030).** Le créneau des panneaux de saisie est choisi **une
  // fois**, en tête de l'espace, et passé en prop. Chaque panneau appelait auparavant
  // `useCreneauDesDuels` pour son compte, le choix vivant en `useState` **local** : autant de
  // sélecteurs divergents que de formats, et le scoreur scorait les rencontres du mauvais départ
  // **avec des identifiants valides, donc sans erreur**. Remonté ici et non dans le store persisté
  // : un créneau qui survit à la fermeture de l'onglet rouvrirait sur le départ de la veille.
  const { departs, liste, departId, choisir } = useCreneauDesDuels(scoreur.tournoi_id)

  return (
    <div>
      <div className="scoreur__barre">
        <p className="carte__etat">
          Session ouverte — <strong>{scoreur.nom}</strong>.
        </p>
        <button
          type="button"
          className="lien"
          disabled={deconnexion.isPending}
          onClick={() => deconnexion.mutate()}
        >
          Fermer ma session
        </button>
      </div>
      <MessageErreur erreur={deconnexion.error} />
      {/* Forfaits de qualification (E04US015) : déclarer / annuler un abandon ou une DSQ. Placé
          au-dessus des duels — un abandon en qualif se prononce avant l'entrée en tableau. */}
      <PanneauForfaitsQualif tournoiId={scoreur.tournoi_id} />

      {/* Le créneau de **tous** les panneaux de saisie ci-dessous, choisi une fois. */}
      <ChoixCreneau departs={liste} valeur={departId} surChangement={choisir} />
      {departs.isSuccess && liste.length === 0 && (
        <p className="carte__etat">Aucun départ n’est encore défini pour ce tournoi.</p>
      )}

      {/* Saisie en duels (E04US013) : le scoreur choisit une phase de tableau, ouvre un duel et le
          score. Monté ici, une fois la session ouverte — comme le poste monte la grille de qualif. */}
      <SaisieDuels tournoiId={scoreur.tournoi_id} departId={departId} />
      {/* Saisie des poules (E05US023) : même pavé, autre navigation — on entre par la poule et le
          tour. L'écran ne s'ouvre que si le créneau porte une phase de poules ; sinon il le dit. */}
      <SaisiePoules tournoiId={scoreur.tournoi_id} departId={departId} />
      <SaisieBigShootOff tournoiId={scoreur.tournoi_id} departId={departId} />
      {/* Saisie du système suisse (E05US030) : même pavé encore, et l'entrée se fait par la
       **ronde** — le décor `RONDES_APPARIEES` du contrat de phase (ADR-0083 §1). */}
      <SaisieSuisse tournoiId={scoreur.tournoi_id} departId={departId} />
      {/* Saisie de la colline (E05US027) : même pavé toujours, et l'entrée se fait par la
          **manche** — même décor `RONDES_APPARIEES` que le suisse. Chaque panneau filtre lui-même
          sur le créneau choisi en tête, il n'y a donc pas de sélecteur à compléter (`DETTE-056`). */}
      <SaisieColline tournoiId={scoreur.tournoi_id} departId={departId} />
    </div>
  )
}
