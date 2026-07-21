// Échappatoire discrète « Changer de rôle » — E00US017, ADR-0042.
//
// Présent dans l'en-tête pour Public / Scoreur / Admin (pas pour la tablette : verrou physique D-13,
// dont la sortie reste le geste « Détacher »). Réinitialise le marqueur de choix **et purge les
// sessions locales** (poste, admin, scoreur) → retour à l'écran de choix. La purge est **nécessaire** :
// sans elle, `resoudreRole` ré-inférerait le rôle depuis un jeton résiduel et l'écran ne
// réapparaîtrait jamais (cf. ADR-0042). Les sessions serveur expirent d'elles-mêmes (comme sur un 401
// / redémarrage serveur) — purge côté client seulement, cohérent avec le périmètre LAN mono-club.

import { useSessionAdminStore } from '../shared/stores/sessionAdminStore'
import { useSessionPosteStore } from '../shared/stores/sessionPosteStore'
import { useSessionRoleStore } from '../shared/stores/sessionRoleStore'
import { useSessionScoreurStore } from '../shared/stores/sessionScoreurStore'

export function ChangerDeRole() {
  const detacherPoste = useSessionPosteStore((s) => s.detacher)
  const effacerAdmin = useSessionAdminStore((s) => s.effacer)
  const effacerScoreur = useSessionScoreurStore((s) => s.effacer)
  const reinitialiserRole = useSessionRoleStore((s) => s.reinitialiser)

  const changer = () => {
    effacerAdmin()
    effacerScoreur()
    detacherPoste()
    reinitialiserRole()
  }

  return (
    <button type="button" className="lien app__changer-role" onClick={changer}>
      Changer de rôle
    </button>
  )
}
