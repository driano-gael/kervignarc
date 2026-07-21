// Confirmation **par calcul d'impact** (E12US007, ADR-0040) — brique transverse partagée.
//
// « Une alerte qui ne chiffre pas son impact est un clic de plus, pas une protection » (P-4). Ce
// composant affiche donc un **corps chiffré** (fourni par l'appelant : « 156 archers perdront leur
// place… ») plutôt qu'un « Êtes-vous sûr ? » creux. Pour une **action massive**, il exige un **geste
// délibéré** : taper un mot (`motRequis`, ex. REPLACER) — impossible par réflexe. Sans `motRequis`,
// c'est une confirmation simple (un bouton). Le composant ne connaît **rien** du métier : il reçoit
// le texte chiffré et le mot, il ne les calcule pas (le calcul est serveur, prévisualisé).
//
// Rendu **inline** (pas de modale à piéger le focus) : cohérent avec le patron de confirmation déjà
// employé dans les features (bascule de boutons), et suffisant pour l'écran admin sur PC.

import { useId, useState } from 'react'

export function ConfirmationChiffree({
  titre,
  motRequis,
  libelleConfirmer,
  enCours = false,
  onConfirmer,
  onAnnuler,
  children,
}: {
  titre: string
  // Mot à taper pour armer la confirmation (action massive). Absent = confirmation simple.
  motRequis?: string
  libelleConfirmer: string
  enCours?: boolean
  onConfirmer: () => void
  onAnnuler: () => void
  children: React.ReactNode
}) {
  const [saisie, setSaisie] = useState('')
  const champId = useId()
  // Comparaison **tolérante à la casse et aux espaces de bord** : on ne piège pas sur une majuscule,
  // le garde-fou est de devoir *taper le mot*, pas de le reproduire au caractère près.
  const motArme = motRequis === undefined || saisie.trim().toUpperCase() === motRequis.toUpperCase()

  return (
    <div className="confirmation" role="group" aria-label={titre}>
      <p className="confirmation__titre">{titre}</p>
      <div className="confirmation__corps">{children}</div>
      {motRequis !== undefined && (
        <p className="confirmation__mot">
          <label htmlFor={champId}>
            Tapez <strong>{motRequis}</strong> pour confirmer
          </label>
          <input
            id={champId}
            className="formulaire__champ"
            value={saisie}
            onChange={(e) => setSaisie(e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
        </p>
      )}
      <div className="confirmation__actions">
        <button
          type="button"
          className="bouton--danger"
          disabled={enCours || !motArme}
          onClick={onConfirmer}
        >
          {libelleConfirmer}
        </button>
        <button type="button" className="bouton--discret" onClick={onAnnuler}>
          Annuler
        </button>
      </div>
    </div>
  )
}
