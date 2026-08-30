// Hooks React Query de la feature « exports » (E09US003, catalogue E16US007).
//
// Le **catalogue** est de l'état serveur en lecture → `useQuery`. Un **téléchargement** est une
// action ponctuelle → `useMutation` (pas de cache : `useQuery` déclencherait un fetch automatique
// et garderait le document en mémoire). `isPending` désactive le bouton, `error` alimente
// `MessageErreur`.

import { useMutation, useQuery } from '@tanstack/react-query'
import { chargerCatalogueExports, telechargerExport } from './api'

export function useCatalogueExports() {
  return useQuery({
    queryKey: ['catalogue-exports'],
    // Le catalogue ne dépend d'aucun tournoi et ne change qu'au redémarrage du serveur : inutile de
    // le recharger à chaque retour sur l'écran.
    staleTime: Number.POSITIVE_INFINITY,
    queryFn: chargerCatalogueExports,
  })
}

export interface DemandeExport {
  chemin: string
  nomSansExtension: string
  format: string
}

// ⚠️ **Un hook par section rendue**, pas un pour l'écran : une mutation partagée désactiverait
// les boutons de tous les documents pendant la génération d'un seul, et afficherait son erreur
// sous chacun d'eux.
export function useTelechargerExport() {
  return useMutation({
    mutationFn: (demande: DemandeExport) =>
      telechargerExport(demande.chemin, demande.nomSansExtension, demande.format),
  })
}
