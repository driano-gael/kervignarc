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

import { useEffect, useId, useRef } from 'react'

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
  // ⚠️ `useId` et **jamais** un identifiant littéral : `BoutonConfirme` monte son dialogue en
  // permanence, y compris fermé, et il y en a **un par ligne** dans la supervision (~30 postes le
  // jour J) comme dans la liste des écrans. Un `id` en dur produisait 30 nœuds homonymes — HTML
  // invalide — et `aria-labelledby` résolvant toujours vers le premier, tout dialogue ouvert était
  // annoncé « Révoquer la cible 1 ? » quelle que soit la ligne. Relevé par quatre axes de revue.
  const idTitre = useId()

  // `showModal()` / `close()` sont **impératifs** : c'est le seul point du composant qui ne se déduit
  // pas du rendu. On les synchronise sur `ouvert` plutôt que d'exposer l'élément, pour que l'appelant
  // ne raisonne qu'en état React.
  useEffect(() => {
    const dialogue = reference.current
    if (dialogue === null) return
    if (ouvert && !dialogue.open) {
      dialogue.showModal()
      // ⚠️ **Le focus se pose ici, et nulle part ailleurs.** `autoFocus` en JSX ne produit pas
      // l'attribut HTML : React appelle `focus()` **au montage**, où le `<dialog>` est encore fermé
      // donc `display: none` — un no-op. Un correctif précédent croyait déplacer le focus par ce
      // biais ; il ne faisait rien du tout, dans les deux branches (2ᵉ passe de revue, vérifié dans
      // le code de React). On focalise donc explicitement, **après** `showModal()`.
      dialogue.querySelector<HTMLButtonElement>('[data-focus-initial]')?.focus()
    }
    if (!ouvert && dialogue.open) dialogue.close()
  }, [ouvert])

  return (
    <dialog
      ref={reference}
      className={`dialogue dialogue--${ton}`}
      aria-labelledby={idTitre}
      // `Échap` ferme nativement : sans ce relais, l'élément se fermerait sans que `ouvert` change,
      // et le dialogue ne pourrait plus jamais être rouvert (l'effet croirait le travail fait).
      onCancel={(evenement) => {
        evenement.preventDefault()
        if (!enCours) onAnnuler()
      }}
    >
      <h2 className="dialogue__titre" id={idTitre}>
        {titre}
      </h2>
      <p className="dialogue__message">{message}</p>
      {detail !== null && detail !== undefined && detail !== '' && (
        <p className="dialogue__detail">{detail}</p>
      )}
      <div className="dialogue__actions">
        {/* Sur un ton `danger`, c'est **« Annuler » qui prend le focus** : `Entrée` par réflexe ne
            doit pas déclencher un geste irréversible. Le libellé qui redit l'action protège de
            l'ambiguïté, pas du réflexe clavier. Le marqueur est lu par l'effet ci-dessus, après
            `showModal()` — cf. son commentaire pour la raison. */}
        <button
          type="button"
          className="bouton--discret"
          disabled={enCours}
          onClick={onAnnuler}
          data-focus-initial={ton === 'danger' ? '' : undefined}
        >
          {libelleAnnuler}
        </button>
        <button
          type="button"
          className={ton === 'danger' ? 'bouton--danger' : undefined}
          disabled={enCours}
          onClick={onConfirmer}
          data-focus-initial={ton === 'danger' ? undefined : ''}
        >
          {enCours ? 'En cours…' : libelleConfirmer}
        </button>
      </div>
    </dialog>
  )
}
