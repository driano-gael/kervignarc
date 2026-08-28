// Confirmation **par calcul d'impact** (E12US007, ADR-0040) — brique transverse partagée.
//
// « Une alerte qui ne chiffre pas son impact est un clic de plus, pas une protection » (P-4) : d'où
// un **corps chiffré** fourni par l'appelant plutôt qu'un « Êtes-vous sûr ? » creux. Pour une
// action **massive**, il exige un **geste délibéré** — taper un mot, impossible par réflexe. Le
// composant ne connaît **rien** du métier : il reçoit le texte chiffré, il ne le calcule pas. Rendu
// **inline** (pas de modale à piéger le focus), cohérent avec le patron déjà employé dans les
// features.

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
      {/* `role="alert"` : l'alerte chiffrée est **annoncée** aux lecteurs d'écran dès qu'elle
          apparaît — c'est le contenu qui décide, il ne doit pas passer inaperçu. */}
      <div className="confirmation__corps" role="alert">
        {children}
      </div>
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
