// Pastille d'état de la connexion temps réel (E00US010, CDC technique §7).
// Visible en permanence : le scoreur doit voir immédiatement une perte de lien.

import { useConnexionStore, type StatutConnexion } from '../stores/connexionStore'

const LIBELLES: Record<StatutConnexion, string> = {
  connexion: 'Connexion…',
  connecte: 'En ligne',
  deconnecte: 'Hors ligne',
}

export function IndicateurConnexion() {
  const statut = useConnexionStore((state) => state.statut)
  return (
    <span className={`indicateur indicateur--${statut}`} role="status">
      <span className="indicateur__pastille" aria-hidden="true" />
      {LIBELLES[statut]}
    </span>
  )
}
