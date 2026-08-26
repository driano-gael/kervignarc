// Hooks React Query des écrans de salle (E07US004, ADR-0064).
//
// **L'affichage se poll**, il ne s'abonne pas. C'est le corollaire direct de la décision
// d'architecture : la fin d'une prise de contrôle naît du *temps qui passe*, qu'aucun événement
// serveur ne peut pousser (ADR-0038 §4, repris par ADR-0064). Un écran abonné au WebSocket
// resterait figé sur un podium expiré tant que personne n'écrirait quelque part.
//
// L'écran décompte **en local** entre deux polls (`reste_s` + une horloge locale), ce qui lui donne
// une reprise à la seconde sans interroger le serveur dix fois par minute — et une reprise correcte
// même s'il perd le réseau au mauvais moment.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  creerEcran,
  getAffichage,
  getEcrans,
  prendreLeControle,
  reglerDeroule,
  reglerPages,
  rendreLaMain,
  renommerEcran,
  supprimerEcran,
  type ReglagePages,
  type VueEcran,
  type VueProgrammee,
} from './api'

/** ~15 s : assez court pour qu'une prise de contrôle atteigne l'écran « en direct » au sens du CA
 * (l'organisateur traverse rarement le gymnase en moins de quinze secondes), assez espacé pour
 * qu'un écran allumé huit heures ne martèle pas le serveur. */
const INTERVALLE_AFFICHAGE_MS = 15000

const cleEcrans = (tournoiId: number) => ['ecrans', tournoiId] as const
const cleAffichage = ['ecran-affichage'] as const
const cleSupervision = (tournoiId: number) => ['supervision', tournoiId] as const

export function useEcrans(tournoiId: number) {
  return useQuery({ queryKey: cleEcrans(tournoiId), queryFn: () => getEcrans(tournoiId) })
}

export function useAffichageEcran(actif: boolean) {
  return useQuery({
    queryKey: cleAffichage,
    queryFn: getAffichage,
    enabled: actif,
    refetchInterval: INTERVALLE_AFFICHAGE_MS,
    staleTime: 0,
  })
}

export function useCreerEcran(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (libelle: string) => creerEcran(tournoiId, libelle),
    onSuccess: () => invalider(queryClient, tournoiId),
  })
}

export function useRenommerEcran(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ posteId, libelle }: { posteId: number; libelle: string }) =>
      renommerEcran(tournoiId, posteId, libelle),
    onSuccess: () => invalider(queryClient, tournoiId),
  })
}

export function useReglerDeroule(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ posteId, vues }: { posteId: number; vues: VueProgrammee[] }) =>
      reglerDeroule(tournoiId, posteId, vues),
    onSuccess: () => invalider(queryClient, tournoiId),
  })
}

export function useReglerPages(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ posteId, pages }: { posteId: number; pages: ReglagePages }) =>
      reglerPages(tournoiId, posteId, pages),
    onSuccess: () => invalider(queryClient, tournoiId),
  })
}

export function useSupprimerEcran(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (posteId: number) => supprimerEcran(tournoiId, posteId),
    onSuccess: () => invalider(queryClient, tournoiId),
  })
}

export function usePrendreLeControle(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      posteId,
      vue,
      dureeS,
    }: {
      posteId: number
      vue: VueEcran
      dureeS: number | null
    }) =>
      prendreLeControle(tournoiId, posteId, {
        vue,
        ...(dureeS === null ? {} : { duree_s: dureeS }),
      }),
    onSuccess: () => invalider(queryClient, tournoiId),
  })
}

export function useRendreLaMain(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (posteId: number) => rendreLaMain(tournoiId, posteId),
    onSuccess: () => invalider(queryClient, tournoiId),
  })
}

/** Toute mutation d'écran ré-invalide **aussi** la console de supervision : c'est là que les écrans
 * et leurs prises de contrôle s'affichent (CA « il apparaît dans la console »), et un tableau qui
 * garderait une ligne périmée après « rendre la main » ferait douter du geste. */
function invalider(
  queryClient: ReturnType<typeof useQueryClient>,
  tournoiId: number,
): Promise<void> {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: cleEcrans(tournoiId) }),
    queryClient.invalidateQueries({ queryKey: cleSupervision(tournoiId) }),
  ]).then(() => undefined)
}
