// Hooks React Query de la feature « identité visuelle du tournoi » (E16US006).
//
// L'identité est de l'état **serveur** : deux accents et la présence de deux logos, scopés à un
// tournoi. Les trois mutations (accents, dépôt, retrait) invalident la même clé — elles rendent
// toutes l'identité complète, mais l'invalidation garde les autres consommateurs à jour (l'écran de
// salle et l'appli publique lisent la même ressource).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  type AccentsAEnregistrer,
  type EmplacementLogo,
  apercuIdentite,
  deposerLogo,
  enregistrerAccents,
  getIdentite,
  retirerLogo,
} from './api'

const cleIdentite = (tournoiId: number) => ['identite', tournoiId] as const

export function useIdentite(tournoiId: number) {
  return useQuery({
    queryKey: cleIdentite(tournoiId),
    queryFn: () => getIdentite(tournoiId),
  })
}

/**
 * L'aperçu d'une saisie en cours — **le contrôle « à la saisie »**.
 *
 * `enabled` sur la validité apparente de la saisie : tant que l'organisateur tape, la valeur est
 * incomplète (`#0b6`), et interroger le serveur à chaque frappe ne produirait que des 422. On
 * n'appelle qu'une fois les six chiffres posés — c'est aussi ce qui évite de faire clignoter le
 * chiffre de contraste.
 *
 * `placeholderData` garde l'aperçu **précédent** affiché pendant le calcul du suivant : sans lui,
 * la zone d'aperçu disparaîtrait à chaque changement de couleur, soit exactement le scintillement
 * qu'un contrôle « à la saisie » doit éviter.
 */
export function useApercuIdentite(accents: AccentsAEnregistrer) {
  const complet = estUneCouleur(accents.primaire) && estUneCouleur(accents.secondaire)
  return useQuery({
    queryKey: ['identite-apercu', accents.primaire, accents.secondaire] as const,
    queryFn: () => apercuIdentite(accents),
    enabled: complet,
    placeholderData: (precedent) => precedent,
  })
}

/**
 * La **même** règle de forme que `Couleur.depuis_hex` côté serveur — et c'est une duplication
 * assumée, non une seconde vérité.
 *
 * Ce prédicat ne décide de **rien** : il ne fait qu'éviter des requêtes vouées au 422 pendant la
 * frappe. Le refus, lui, reste au serveur, et un `#zzz` qui passerait ici serait refusé là-bas. La
 * différence avec la dérivation — qu'on ne duplique surtout pas — est qu'une divergence ici est
 * **bruyante** (une requête part et échoue), alors qu'un contraste faux serait silencieux.
 */
export function estUneCouleur(saisie: string): boolean {
  return /^#[0-9a-fA-F]{6}$/.test(saisie.trim())
}

export function useEnregistrerAccents(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (accents: AccentsAEnregistrer) => enregistrerAccents(tournoiId, accents),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleIdentite(tournoiId) }),
  })
}

export function useDeposerLogo(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ emplacement, fichier }: { emplacement: EmplacementLogo; fichier: File }) =>
      deposerLogo(tournoiId, emplacement, fichier),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleIdentite(tournoiId) }),
  })
}

export function useRetirerLogo(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (emplacement: EmplacementLogo) => retirerLogo(tournoiId, emplacement),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cleIdentite(tournoiId) }),
  })
}
