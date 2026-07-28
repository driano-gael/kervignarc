import { useId, useState } from 'react'

/**
 * Aide contextuelle d'un écran d'administration — **patron unique** (E14US002).
 *
 * Répond au retour de la démo du 27/07/2026 : « une explication de ce qui est saisissable et
 * pourquoi ; je ne veux pas de formation ». Un composant unique, réutilisé par toutes les
 * destinations admin, de sorte qu'un changement de rendu (ton, forme, accessibilité) se fasse **une
 * fois** — même logique que `MessageErreur` (E00US013, DETTE-004).
 *
 * Forme retenue (cadrage du 28/07/2026) : un bouton « ⓘ Aide » **masqué par défaut**, l'aide se
 * **déploie au tap**. Choix dicté par la contrainte tactile — ~30 tablettes BYOD : les infobulles au
 * survol (`title=`) ne s'affichent pas au doigt, elles sont donc proscrites pour porter de
 * l'information. Le bouton, lui, est toujours visible : la découvrabilité prime (« sans formation »),
 * l'encombrement vertical est repoussé derrière le tap.
 *
 * Le **contenu** est fourni par l'appelant (dictionnaire centralisé côté coquille) : ce composant ne
 * connaît aucun écran, il ne fait qu'afficher/replier le texte qu'on lui passe. Sans texte, il ne
 * rend rien (l'écran reste inchangé) — comme `MessageErreur` s'efface quand l'erreur est nulle.
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
