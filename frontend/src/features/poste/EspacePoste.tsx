// Espace poste (E04US001) — l'écran d'une tablette de cible, ouvert au montage.
//
// Le bénévole **scanne le QR** de sa cible (l'URL pré-remplit le code → rattachement automatique) ou
// **tape le code** imprimé en secours. Une session de poste s'ouvre alors, persistée localement pour
// survivre à la fermeture de l'onglet, à une veille, à un redémarrage — la tablette **retrouve sa
// cible sans rien redemander** (D-13). Le poste peut choisir sa **luminosité** (D-26), qui revient
// toute seule. La **saisie** des scores relève d'E04US002 ; ici, on rattache et on détache.

import { useEffect, useRef, useState } from 'react'
import { Saisie } from '../saisie/Saisie'
import { ErreurApi } from '../../shared/api/client'
import { type CiblePoste, useSessionPosteStore } from '../../shared/stores/sessionPosteStore'
import type { Theme } from '../../shared/theme'
import { useDeconnexionPoste, useRattacherPoste, useVerifierPoste } from './hooks'
import { oublierCodePosteUrl } from './url'

export function EspacePoste({ codeInitial }: { codeInitial: string | null }) {
  const jeton = useSessionPosteStore((s) => s.jeton)
  const poste = useSessionPosteStore((s) => s.poste)
  // Réouverture : dès qu'un jeton est présent, on vérifie qu'il vaut toujours (révocation → purge).
  useVerifierPoste(jeton !== null)

  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">Poste de saisie</h2>
      {jeton !== null && poste !== null ? (
        <PosteRattache poste={poste} />
      ) : (
        <FormulaireRattachement codeInitial={codeInitial} />
      )}
      <BasculeTheme />
    </section>
  )
}

function FormulaireRattachement({ codeInitial }: { codeInitial: string | null }) {
  const [code, setCode] = useState(codeInitial ?? '')
  const rattacher = useRattacherPoste()
  const entreeValide = code.trim() !== ''

  // Scan du QR : l'URL a pré-rempli un code → rattachement **automatique**, une seule fois.
  const autoFait = useRef(false)
  useEffect(() => {
    if (!autoFait.current && codeInitial !== null && codeInitial.trim() !== '') {
      autoFait.current = true
      rattacher.mutate(codeInitial)
    }
  }, [codeInitial, rattacher])

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!entreeValide) return
    rattacher.mutate(code)
  }

  return (
    <div>
      <p className="carte__etat">
        Scannez le QR de votre cible, ou entrez le code imprimé en dessous pour rattacher cette
        tablette.
      </p>
      <form className="formulaire" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Code de la cible"
          aria-label="Code de la cible"
          autoComplete="one-time-code"
          autoCapitalize="characters"
        />
        <button type="submit" disabled={rattacher.isPending || !entreeValide}>
          Rattacher cette tablette
        </button>
      </form>
      <MessageErreur erreur={rattacher.error} />
    </div>
  )
}

function PosteRattache({ poste }: { poste: CiblePoste }) {
  const deconnexion = useDeconnexionPoste()

  const detacher = () => {
    // Retirer `?poste=…` de l'URL **avant** de détacher : sinon `codePoste` resterait non nul et l'app
    // réafficherait l'écran de poste (voire le re-rattacherait automatiquement) juste après.
    oublierCodePosteUrl()
    deconnexion.mutate()
  }

  return (
    <div>
      <Saisie tournoiId={poste.tournoi_id} cibleIndex={poste.cible_index} />
      <button
        type="button"
        className="lien saisie__detacher"
        disabled={deconnexion.isPending}
        onClick={detacher}
      >
        Détacher cette tablette
      </button>
      <MessageErreur erreur={deconnexion.error} />
    </div>
  )
}

// Luminosité du poste (D-26) : « Système » (suit `prefers-color-scheme`), « Clair » ou « Sombre »
// forcés. Le choix est persisté et revient tout seul à la réouverture (cf. `sessionPosteStore`).
function BasculeTheme() {
  const theme = useSessionPosteStore((s) => s.theme)
  const definirTheme = useSessionPosteStore((s) => s.definirTheme)
  const options: { valeur: Theme | null; libelle: string }[] = [
    { valeur: null, libelle: 'Système' },
    { valeur: 'clair', libelle: 'Clair' },
    { valeur: 'sombre', libelle: 'Sombre' },
  ]

  return (
    <div className="bascule-theme" role="group" aria-label="Luminosité de ce poste">
      <span className="carte__soustitre">Luminosité</span>
      {options.map((o) => (
        <button
          key={o.libelle}
          type="button"
          className="lien"
          aria-pressed={theme === o.valeur}
          onClick={() => definirTheme(o.valeur)}
        >
          {o.libelle}
        </button>
      ))}
    </div>
  )
}

// DETTE-004 (docs/dette.md) : énième copie conforme de ce composant, un par feature. À extraire dans
// `shared/` — E00US013. Non factorisée ici : le faire toucherait les autres features, hors périmètre.
function MessageErreur({ erreur }: { erreur: Error | null }) {
  if (erreur === null) return null
  const message = erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
  return (
    <p className="carte__etat carte__etat--erreur" role="alert">
      {message}
    </p>
  )
}
