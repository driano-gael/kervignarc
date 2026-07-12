// Hooks React Query de la feature « admin » (E10US002).
//
// L'état de configuration de l'accès est une lecture serveur (query) ; définir/se connecter/se
// déconnecter sont des mutations. Une définition ou connexion réussie enregistre le jeton dans
// le store de session ; la déconnexion l'efface (best-effort côté serveur).

import { useMutation, useQuery } from '@tanstack/react-query'
import { useSessionAdminStore } from '../../shared/stores/sessionAdminStore'
import { configurerAdmin, connexionAdmin, deconnexionAdmin, getEtatAuth } from './api'

const CLE_ETAT_AUTH = ['auth', 'etat'] as const

export function useEtatAuth() {
  return useQuery({ queryKey: CLE_ETAT_AUTH, queryFn: getEtatAuth })
}

export function useConfigurerAdmin() {
  const definir = useSessionAdminStore((s) => s.definir)
  return useMutation({
    mutationFn: configurerAdmin,
    onSuccess: (reponse) => definir(reponse.jeton),
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
  return useMutation({
    mutationFn: deconnexionAdmin,
    // Purge locale quoi qu'il arrive : même si l'appel serveur échoue, l'admin est déconnecté côté client.
    onSettled: () => effacer(),
  })
}
