// Hooks React Query de la feature « admin » (E10US002).
//
// L'état de configuration de l'accès est une lecture serveur (query) ; définir/se connecter/se
// déconnecter sont des mutations. Une définition ou connexion réussie enregistre le jeton dans
// le store de session ; la déconnexion l'efface (best-effort côté serveur).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSessionAdminStore } from '../../shared/stores/sessionAdminStore'
import { configurerAdmin, connexionAdmin, deconnexionAdmin, getEtatAuth } from './api'

const CLE_ETAT_AUTH = ['auth', 'etat'] as const

export function useEtatAuth() {
  return useQuery({ queryKey: CLE_ETAT_AUTH, queryFn: getEtatAuth })
}

export function useConfigurerAdmin() {
  const definir = useSessionAdminStore((s) => s.definir)
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: configurerAdmin,
    onSuccess: (reponse) => {
      definir(reponse.jeton)
      // L'accès est désormais configuré : invalide l'état mis en cache (sinon un logout
      // ré-afficherait à tort l'écran « définir l'accès » avant refetch).
      queryClient.invalidateQueries({ queryKey: CLE_ETAT_AUTH })
    },
  })
}

export function useConnexionAdmin() {
  const definir = useSessionAdminStore((s) => s.definir)
  return useMutation({
    mutationFn: connexionAdmin,
    onSuccess: (reponse) => definir(reponse.jeton),
  })
}

export function useDeconnexionAdmin() {
  const effacer = useSessionAdminStore((s) => s.effacer)
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deconnexionAdmin,
    // Purge locale quoi qu'il arrive : même si l'appel serveur échoue, l'admin est déconnecté
    // côté client. On rafraîchit l'état d'accès pour repartir de l'écran de connexion à jour.
    onSettled: () => {
      effacer()
      queryClient.invalidateQueries({ queryKey: CLE_ETAT_AUTH })
    },
  })
}
