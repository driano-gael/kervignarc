// Hooks React Query de la feature « scoreur-session » (E10US003).
//
// Connexion et déconnexion sont des **mutations**. Une connexion réussie enregistre le jeton et
// l'identité du scoreur dans le store de session ; la déconnexion les efface (best-effort côté
// serveur — la session locale est purgée quoi qu'il arrive).

import { useMutation } from '@tanstack/react-query'
import { useSessionScoreurStore } from '../../shared/stores/sessionScoreurStore'
import { connexionScoreur, deconnexionScoreur } from './api'

export function useConnexionScoreur() {
  const definir = useSessionScoreurStore((s) => s.definir)
  return useMutation({
    mutationFn: connexionScoreur,
    onSuccess: (reponse) => definir({ jeton: reponse.jeton, scoreur: reponse.scoreur }),
  })
}

export function useDeconnexionScoreur() {
  const effacer = useSessionScoreurStore((s) => s.effacer)
  return useMutation({
    mutationFn: deconnexionScoreur,
    // Purge locale quoi qu'il arrive : même si l'appel serveur échoue, le scoreur est déconnecté
    // côté client (on revient au formulaire de code).
    onSettled: () => effacer(),
  })
}
