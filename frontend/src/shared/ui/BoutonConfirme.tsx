// Un bouton dont l'action passe par une confirmation — retour maquettes du 04/08/2026 (A15).
//
// C'est la forme sous laquelle les huit `window.confirm` du produit se remplacent : chacun était
// « un bouton + une question », et les réécrire un par un aurait demandé partout le même `useState`
// d'ouverture, la même remise à zéro et le même risque d'oubli (un dialogue qu'on n'a pas refermé
// après succès reste ouvert sur un écran temps réel).
//
// Le composant possède donc **le bouton et son dialogue**, et l'appelant ne voit qu'un élément.
// Quand le déclencheur n'est pas un bouton ordinaire — une ligne de tableau, un lien — on descend
// d'un cran sur `DialogueConfirmation`, qui ne fait aucune supposition sur le déclencheur.

import { useState } from 'react'
import { DialogueConfirmation, type TonConfirmation } from './DialogueConfirmation'

export function BoutonConfirme({
  libelle,
  titre,
  message,
  detail,
  libelleConfirmer,
  ton = 'normal',
  className,
  disabled = false,
  enCours = false,
  onConfirmer,
}: {
  /** Ce qu'on lit sur le bouton, avant toute question. */
  libelle: string
  titre: string
  message: string
  detail?: string | null
  /** Le libellé du bouton de confirmation. À défaut, on **reprend celui du déclencheur** : c'est le
   * même geste, et le redire avec d'autres mots ferait douter qu'il s'agisse bien du même. */
  libelleConfirmer?: string
  ton?: TonConfirmation
  className?: string
  disabled?: boolean
  enCours?: boolean
  onConfirmer: () => void
}) {
  const [ouvert, setOuvert] = useState(false)

  return (
    <>
      <button
        type="button"
        className={className}
        disabled={disabled}
        onClick={() => setOuvert(true)}
      >
        {libelle}
      </button>
      <DialogueConfirmation
        ouvert={ouvert}
        titre={titre}
        message={message}
        detail={detail}
        libelleConfirmer={libelleConfirmer ?? libelle}
        ton={ton}
        enCours={enCours}
        onAnnuler={() => setOuvert(false)}
        onConfirmer={() => {
          // On ferme **avant** d'agir : la mutation est asynchrone et son résultat s'affiche sur
          // l'écran derrière (message d'erreur, compte de duels partis). Laisser le dialogue ouvert
          // le temps de l'aller-retour masquerait précisément ce qu'on vient déclencher.
          setOuvert(false)
          onConfirmer()
        }}
      />
    </>
  )
}
