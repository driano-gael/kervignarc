// Branche le client WebSocket au cycle de vie React (E00US010).
//
// Reflète le statut de connexion dans le store UI et, à chaque événement diffusé,
// **invalide** le cache React Query (intégration temps réel → refetch ciblé plus tard,
// guide §8). Un seul point de câblage du temps réel dans l'app.

import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useConnexionStore } from '../stores/connexionStore'
import { RealtimeClient } from './RealtimeClient'

export function useRealtime(): void {
  const queryClient = useQueryClient()
  const setStatut = useConnexionStore((state) => state.setStatut)

  useEffect(() => {
    const client = new RealtimeClient({
      onStatut: setStatut,
      onEvenement: () => {
        void queryClient.invalidateQueries()
      },
    })
    client.connecter()
    return () => client.fermer()
  }, [queryClient, setStatut])
}
