// Hooks React Query de la feature « poste » (E04US001).
//
// Rattachement et détachement sont des **mutations** (elles modifient la session locale) ; la
// vérification de cible à l'ouverture est une **requête** dont le seul effet utile est de déclencher
// la purge sur 401 (révocation « tournoi terminé », serveur redémarré).

import { useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useSessionPosteStore } from '../../shared/stores/sessionPosteStore'
import { cibleDuPoste, deconnexionPoste, heartbeatPoste, rattacherPoste } from './api'

// Intervalle du heartbeat (E12US001, ADR-0038). Doit rester **inférieur** au seuil hors-ligne du
// serveur (30 s), avec de la marge pour un ping manqué — les deux valeurs sont liées.
const INTERVALLE_HEARTBEAT_MS = 10_000

export function useRattacherPoste() {
  const definir = useSessionPosteStore((s) => s.definir)
  return useMutation({
    mutationFn: rattacherPoste,
    onSuccess: (reponse) => definir({ jeton: reponse.jeton, poste: reponse.poste }),
  })
}

export function useDeconnexionPoste() {
  const detacher = useSessionPosteStore((s) => s.detacher)
  return useMutation({
    mutationFn: deconnexionPoste,
    // Détachement **explicite** quoi qu'il arrive : même si l'appel serveur échoue, la tablette quitte
    // le mode poste côté client (`detacher`, pas `effacer`) → retour à l'app normale, pas au
    // formulaire de rattachement. Le nettoyage du `?poste=` de l'URL est fait par l'appelant.
    onSettled: () => detacher(),
  })
}

// À l'ouverture (réouverture après coupure), vérifie que la session vaut toujours : un 401 purge le
// rattachement via le client HTTP (`enregistrerSurNonAutorisePoste`) et l'UI repasse sur le code.
// Actif seulement quand un jeton est présent ; pas de re-tentative (un 401 n'est pas à réessayer).
export function useVerifierPoste(actif: boolean) {
  return useQuery({
    queryKey: ['poste-cible'],
    queryFn: cibleDuPoste,
    enabled: actif,
    retry: false,
    staleTime: 30_000,
  })
}

// Signale la présence de la tablette tant que sa session est active (E12US001, ADR-0038). Un premier
// battement **immédiat** (ne pas attendre l'intervalle pour apparaître « en ligne »), puis périodique.
// Les échecs sont **avalés** : un ping raté fera simplement basculer le poste « hors ligne » dans la
// console (le but même de la supervision) ; un 401 aura déjà purgé la session dans `fetchJson`.
export function useHeartbeatPoste(actif: boolean) {
  useEffect(() => {
    if (!actif) return
    const battre = () => {
      void heartbeatPoste().catch(() => {})
    }
    battre()
    const id = window.setInterval(battre, INTERVALLE_HEARTBEAT_MS)
    return () => window.clearInterval(id)
  }, [actif])
}
