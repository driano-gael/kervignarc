// Échappatoire discrète « Changer de rôle » — E00US017, ADR-0042.
//
// Présent dans l'en-tête pour Public / Scoreur / Admin (pas pour la tablette : verrou physique D-13,
// dont la sortie reste le geste « Détacher »). Réinitialise le marqueur de choix **et purge les
// sessions locales** (poste, admin, scoreur) → retour à l'écran de choix. La purge est **nécessaire** :
// sans elle, `resoudreRole` ré-inférerait le rôle depuis un jeton résiduel et l'écran ne
// réapparaîtrait jamais (cf. ADR-0042). Les sessions serveur expirent d'elles-mêmes (comme sur un 401
// / redémarrage serveur) — purge côté client seulement, cohérent avec le périmètre LAN mono-club.

import { useSessionAdminStore } from '../stores/sessionAdminStore'
import { useSessionPosteStore } from '../stores/sessionPosteStore'
import { useSessionRoleStore } from '../stores/sessionRoleStore'
import { useSessionScoreurStore } from '../stores/sessionScoreurStore'
import { naviguer } from '../navigation/useChemin'

// `libelle` : le même geste s'appelle « Changer de rôle » dans l'en-tête (action rare, ton neutre) et
// « Choisir un autre appareil » au pied de l'écran de connexion, où c'est la question que se pose
// l'utilisateur (A01, 04/08/2026). Un paramètre plutôt qu'un second composant : la purge des quatre
// stores est la partie risquée, la dupliquer pour changer trois mots serait le meilleur moyen d'en
// oublier un le jour où l'on ajoute une session.
export function ChangerDeRole({ libelle = 'Changer de rôle' }: { libelle?: string }) {
  const detacherPoste = useSessionPosteStore((s) => s.detacher)
  const effacerAdmin = useSessionAdminStore((s) => s.effacer)
  const effacerScoreur = useSessionScoreurStore((s) => s.effacer)
  const reinitialiserRole = useSessionRoleStore((s) => s.reinitialiser)

  const changer = () => {
    effacerAdmin()
    effacerScoreur()
    detacherPoste()
    reinitialiserRole()
    // Depuis E14US003, **l'adresse fait partie de l'état** : purger les sessions sans revenir à `/`
    // laisserait l'URL sur `/admin`, qui l'emporte sur le marqueur de choix (`mondeAServir`) — le
    // bouton n'aurait alors aucun effet visible, il rouvrirait le monde qu'on vient de quitter.
    // `remplacer` : c'est une sortie **subie** du monde qu'on quitte, l'empiler laisserait le bouton
    // « précédent » y ramener aussitôt (même raisonnement qu'ADR-0059 sur les corrections d'adresse).
    naviguer('/', { remplacer: true })
  }

  return (
    <button type="button" className="lien app__changer-role" onClick={changer}>
      {libelle}
    </button>
  )
}
