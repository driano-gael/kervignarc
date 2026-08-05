// Dialogue de confirmation — retour maquettes du 04/08/2026 (A15).
//
// *« La confirmation passe par un window.confirm que le code signale comme provisoire — que veux-tu à
// la place ? → une pop-up propre et bien design. »*
//
// **Le provisoire s'était répandu.** Ce n'était pas un `window.confirm` mais **huit**, sur les gestes
// les plus lourds du produit : lancer un tour, terminer un tournoi, annuler, archiver, révoquer un
// écran, un poste, perdre un barrage en cours. Tous portaient la même note « en attendant une friction
// plus riche ». Un `confirm` natif a trois défauts qui comptent ici : il **bloque le fil** (les
// requêtes en vol et le rendu s'arrêtent, sur un écran temps réel c'est visible), il ne peut **rien
// nommer** (ni le ton, ni les conséquences chiffrées, ni un libellé de bouton qui redit le geste — on
// lit « OK / Annuler », ce qui est ambigu quand le geste *est* une annulation), et son apparence
// dépend du navigateur, donc du parc — ce qui contredit le CDC design.
//
// **Pourquoi `<dialog>` natif et pas une librairie.** Règle 11 : « stdlib ou quelques lignes maison
// préférées ». `showModal()` fournit gratuitement le piège de focus, la fermeture par `Échap`, l'inertie
// de l'arrière-plan et le `::backdrop` — c'est-à-dire exactement ce pour quoi on prendrait une
// dépendance. Support : Chrome 37+, Safari 15.4+, Firefox 98+ ; le parc du jour J est BYOD mais un
// navigateur antérieur à 2022 ne ferait pas tourner le reste de l'app non plus.

import { useEffect, useRef } from 'react'

export type TonConfirmation = 'normal' | 'danger'

export function DialogueConfirmation({
  ouvert,
  titre,
  message,
  detail,
  libelleConfirmer = 'Confirmer',
  libelleAnnuler = 'Annuler',
  ton = 'normal',
  enCours = false,
  onConfirmer,
  onAnnuler,
}: {
  ouvert: boolean
  titre: string
  /** La phrase qui dit **ce qui va se passer**, au présent et en clair. */
  message: string
  /** Le détail chiffré ou la conséquence, quand il y en a une. Facultatif. */
  detail?: string | null
  libelleConfirmer?: string
  libelleAnnuler?: string
  /** `danger` pour ce qui **détruit ou fige** (annuler, archiver, révoquer). */
  ton?: TonConfirmation
  /** La mutation est en vol : on désactive sans fermer, sinon le clic peut partir deux fois. */
  enCours?: boolean
  onConfirmer: () => void
  onAnnuler: () => void
}) {
  const reference = useRef<HTMLDialogElement>(null)

  // `showModal()` / `close()` sont **impératifs** : c'est le seul point du composant qui ne se déduit
  // pas du rendu. On les synchronise sur `ouvert` plutôt que d'exposer l'élément, pour que l'appelant
  // ne raisonne qu'en état React.
  useEffect(() => {
    const dialogue = reference.current
    if (dialogue === null) return
    if (ouvert && !dialogue.open) dialogue.showModal()
    if (!ouvert && dialogue.open) dialogue.close()
  }, [ouvert])

  return (
    <dialog
      ref={reference}
      className={`dialogue dialogue--${ton}`}
      aria-labelledby="dialogue-titre"
      // `Échap` ferme nativement : sans ce relais, l'élément se fermerait sans que `ouvert` change,
      // et le dialogue ne pourrait plus jamais être rouvert (l'effet croirait le travail fait).
      onCancel={(evenement) => {
        evenement.preventDefault()
        if (!enCours) onAnnuler()
      }}
    >
      <h2 className="dialogue__titre" id="dialogue-titre">
        {titre}
      </h2>
      <p className="dialogue__message">{message}</p>
      {detail !== null && detail !== undefined && detail !== '' && (
        <p className="dialogue__detail">{detail}</p>
      )}
      <div className="dialogue__actions">
        <button type="button" className="bouton--discret" disabled={enCours} onClick={onAnnuler}>
          {libelleAnnuler}
        </button>
        <button
          type="button"
          className={ton === 'danger' ? 'bouton--danger' : undefined}
          disabled={enCours}
          onClick={onConfirmer}
          // Le geste confirmé prend le focus à l'ouverture : c'est celui qu'on est venu faire, et
          // `Entrée` doit tomber dessus. Le garde-fou reste le **libellé**, qui redit le geste
          // (« Lancer le tour ») là où un `confirm` natif n'offre que « OK ».
          autoFocus
        >
          {enCours ? 'En cours…' : libelleConfirmer}
        </button>
      </div>
    </dialog>
  )
}
