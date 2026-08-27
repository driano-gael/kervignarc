import { useId, useState } from 'react'

/**
 * Aide contextuelle d'un écran d'administration — **patron unique** (E14US002).
 *
 * Répond au retour du 27/07/2026 : « une explication de ce qui est saisissable ; je ne veux pas de
 * formation ». ⚠️ Forme retenue (28/07/2026) : un bouton toujours visible, l'aide se **déploie au
 * tap** — les infobulles au survol ne s'affichent pas au doigt, et le parc est tactile. Le contenu
 * vient de l'appelant : sans texte, il ne rend rien, comme `MessageErreur`.
 */
export function AideEcran({ texte }: { texte: string | null | undefined }) {
  const [ouvert, setOuvert] = useState(false)
  // `useId` donne un identifiant stable et unique (rendu serveur/client cohérent) pour relier le
  // bouton à son panneau via `aria-controls` — un lecteur d'écran sait ce que le bouton déploie.
  const panneauId = useId()

  if (!texte) return null

  return (
    <div className="aide-ecran">
      <button
        type="button"
        className="aide-ecran__bouton"
        aria-expanded={ouvert}
        aria-controls={panneauId}
        onClick={() => setOuvert((o) => !o)}
      >
        <span className="aide-ecran__glyphe" aria-hidden="true">
          ⓘ
        </span>{' '}
        Aide
      </button>
      {/* Le panneau reste dans le DOM et se cache par `hidden` (plutôt que d'être démonté) : ainsi
          `aria-controls` pointe toujours vers un élément réel, et l'attribut `hidden` le retire à la
          fois de l'affichage et de l'arbre d'accessibilité quand l'aide est repliée. */}
      <p id={panneauId} className="aide-ecran__panneau" role="note" hidden={!ouvert}>
        {texte}
      </p>
    </div>
  )
}
