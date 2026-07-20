// Pastille d'état de la connexion temps réel (E00US010, complétée E04US009 ; CDC technique §7).
// Visible en permanence : le scoreur (et le poste) doivent voir immédiatement une perte de lien —
// et, depuis E04US009, savoir si des saisies **attendent** d'être renvoyées ou sont en cours de
// **synchronisation**. L'état affiché est dérivé (logique pure `etatIndicateur`) des deux signaux.

import { useConnexionStore } from '../stores/connexionStore'
import { useFileHorsLigneStore } from '../stores/fileHorsLigneStore'
import { etatIndicateur } from './indicateur'

export function IndicateurConnexion() {
  const statut = useConnexionStore((state) => state.statut)
  const nbEnAttente = useFileHorsLigneStore((state) => state.enAttente.length)
  const synchronisation = useFileHorsLigneStore((state) => state.synchronisation)
  const { classe, libelle } = etatIndicateur(statut, nbEnAttente, synchronisation)
  return (
    <span className={`indicateur indicateur--${classe}`} role="status">
      <span className="indicateur__pastille" aria-hidden="true" />
      {libelle}
    </span>
  )
}
