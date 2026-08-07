// Hooks React Query de la feature « patrimoine » (E01US023, ADR-0060).
//
// Les listes de bibliothèque sont de l'état **serveur** ; créer, pré-charger, assembler et
// promouvoir sont des **mutations** qui les invalident.
//
// Les clés de cache de bibliothèque ne sont **pas** paramétrées par un tournoi — comme `clubs` et
// `gabarits`, et contrairement à `categories`/`blasons` d'un tournoi. C'est le cache qui reflète le
// modèle : une brique du patrimoine n'appartient à aucune édition.
//
// ⚠️ Une **promotion** touche deux caches : la copie du tournoi (inchangée, mais l'écran l'affiche
// à côté) et la bibliothèque (modifiée). Un assemblage aussi, dans l'autre sens. On invalide donc
// les deux côtés à chaque fois — un seul suffirait la plupart du temps, mais l'écran d'assemblage
// montre justement les deux, et un oubli s'y verrait comme une liste qui ne bouge pas.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { cleBlasons } from '../blasons/hooks'
import {
  appliquerFormat,
  assemblerTournoi,
  creerBlasonBibliotheque,
  creerCategorieBibliotheque,
  creerFormat,
  dupliquerBlasonBibliotheque,
  dupliquerCategorieBibliotheque,
  dupliquerFormat,
  getBlasonsBibliotheque,
  getCategoriesBibliotheque,
  getFormats,
  importerClubs,
  modifierFormat,
  type NouveauBlasonBibliotheque,
  type NouveauFormat,
  type NouvelleCategorieBibliotheque,
  prechargerFftaBibliotheque,
  prechargerPresetsFormats,
  promouvoirBlason,
  promouvoirCategorie,
  promouvoirFormat,
  type ModifierCategorieBibliotheque,
  renommerCategorieBibliotheque,
  supprimerBlasonBibliotheque,
  supprimerCategorieBibliotheque,
  supprimerFormat,
} from './api'

export const cleCategoriesBibliotheque = ['patrimoine', 'categories'] as const
export const cleBlasonsBibliotheque = ['patrimoine', 'blasons'] as const
export const cleFormats = ['patrimoine', 'formats'] as const
const cleCategoriesTournoi = (tournoiId: number) => ['categories', tournoiId] as const

export function useCategoriesBibliotheque() {
  return useQuery({ queryKey: cleCategoriesBibliotheque, queryFn: getCategoriesBibliotheque })
}

export function useBlasonsBibliotheque() {
  return useQuery({ queryKey: cleBlasonsBibliotheque, queryFn: getBlasonsBibliotheque })
}

export function useFormats() {
  return useQuery({ queryKey: cleFormats, queryFn: getFormats })
}

/** Invalide les deux listes de bibliothèque (les catégories dépendent des blasons, E01US006). */
function useInvaliderBibliotheque() {
  const queryClient = useQueryClient()
  return () => {
    queryClient.invalidateQueries({ queryKey: cleCategoriesBibliotheque })
    queryClient.invalidateQueries({ queryKey: cleBlasonsBibliotheque })
  }
}

export function useCreerCategorieBibliotheque() {
  const invalider = useInvaliderBibliotheque()
  return useMutation({
    mutationFn: (entree: NouvelleCategorieBibliotheque) => creerCategorieBibliotheque(entree),
    onSuccess: invalider,
  })
}

export function useCreerBlasonBibliotheque() {
  const invalider = useInvaliderBibliotheque()
  return useMutation({
    mutationFn: (entree: NouveauBlasonBibliotheque) => creerBlasonBibliotheque(entree),
    onSuccess: invalider,
  })
}

export function useRenommerCategorieBibliotheque() {
  const invalider = useInvaliderBibliotheque()
  return useMutation({
    // `entree` est l'entité **complète** : le PUT est total, un champ omis serait effacé (cf. api.ts).
    mutationFn: ({ id, entree }: { id: number; entree: ModifierCategorieBibliotheque }) =>
      renommerCategorieBibliotheque(id, entree),
    onSuccess: invalider,
  })
}

export function useDupliquerCategorieBibliotheque() {
  const invalider = useInvaliderBibliotheque()
  return useMutation({
    mutationFn: ({ id, nom }: { id: number; nom: string }) =>
      dupliquerCategorieBibliotheque(id, nom),
    onSuccess: invalider,
  })
}

export function useDupliquerBlasonBibliotheque() {
  const invalider = useInvaliderBibliotheque()
  return useMutation({
    mutationFn: ({ id, nom }: { id: number; nom: string }) => dupliquerBlasonBibliotheque(id, nom),
    onSuccess: invalider,
  })
}

export function useSupprimerCategorieBibliotheque() {
  const invalider = useInvaliderBibliotheque()
  return useMutation({
    mutationFn: (id: number) => supprimerCategorieBibliotheque(id),
    onSuccess: invalider,
  })
}

export function useSupprimerBlasonBibliotheque() {
  const invalider = useInvaliderBibliotheque()
  return useMutation({
    mutationFn: (id: number) => supprimerBlasonBibliotheque(id),
    onSuccess: invalider,
  })
}

export function usePrechargerFftaBibliotheque() {
  const invalider = useInvaliderBibliotheque()
  return useMutation({ mutationFn: prechargerFftaBibliotheque, onSuccess: invalider })
}

export function useAssemblerTournoi(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => assemblerTournoi(tournoiId),
    // L'assemblage crée les **copies du tournoi** : ce sont ces listes-là qui changent.
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cleCategoriesTournoi(tournoiId) })
      queryClient.invalidateQueries({ queryKey: cleBlasons(tournoiId) })
    },
  })
}

export function usePromouvoirCategorie(tournoiId: number) {
  const queryClient = useQueryClient()
  const invalider = useInvaliderBibliotheque()
  return useMutation({
    mutationFn: (id: number) => promouvoirCategorie(id),
    onSuccess: () => {
      invalider()
      queryClient.invalidateQueries({ queryKey: cleCategoriesTournoi(tournoiId) })
    },
  })
}

export function usePromouvoirBlason(tournoiId: number) {
  const queryClient = useQueryClient()
  const invalider = useInvaliderBibliotheque()
  return useMutation({
    mutationFn: (id: number) => promouvoirBlason(id),
    onSuccess: () => {
      invalider()
      queryClient.invalidateQueries({ queryKey: cleBlasons(tournoiId) })
    },
  })
}

function useInvaliderFormats() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: cleFormats })
}

export function useCreerFormat() {
  const invalider = useInvaliderFormats()
  return useMutation({
    mutationFn: (entree: NouveauFormat) => creerFormat(entree),
    onSuccess: invalider,
  })
}

export function useModifierFormat() {
  const invalider = useInvaliderFormats()
  return useMutation({
    mutationFn: ({ id, entree }: { id: number; entree: NouveauFormat }) =>
      modifierFormat(id, entree),
    onSuccess: invalider,
  })
}

export function useDupliquerFormat() {
  const invalider = useInvaliderFormats()
  return useMutation({
    mutationFn: ({ id, nom }: { id: number; nom: string }) => dupliquerFormat(id, nom),
    onSuccess: invalider,
  })
}

export function useSupprimerFormat() {
  const invalider = useInvaliderFormats()
  return useMutation({ mutationFn: (id: number) => supprimerFormat(id), onSuccess: invalider })
}

export function usePrechargerPresetsFormats() {
  const invalider = useInvaliderFormats()
  return useMutation({ mutationFn: prechargerPresetsFormats, onSuccess: invalider })
}

export function useAppliquerFormat(tournoiId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (formatId: number) => appliquerFormat(tournoiId, formatId),
    // Applique = **compose le déroulé** du tournoi, et l'instancie dans chaque créneau. Plusieurs
    // caches en dépendent, pas un : la séquence de phases, mais aussi le **barème** et le **grain
    // de validation**, qui vivent *dans* la phase de qualification et sont servis par leurs propres
    // clés. Ne rafraîchir que `phases` laissait l'écran « Barème & validation » afficher l'ancien
    // réglage — soit l'étape suivante prescrite par la recette.
    //
    // ⚠️ **Et l'avancement de chaque créneau, et le suivi du déroulé** (ADR-0076, revue E01US025).
    // Les quatre mutations d'édition du déroulé (`phases/hooks.ts`) invalident bien ces deux
    // racines ; celle-ci est la **cinquième voie d'écriture** et avait été oubliée. Résultat :
    // après « appliquer un format », le pilotage de créneau affichait encore « ce créneau ne joue
    // encore aucune phase » alors que le déroulé venait d'y être instancié.
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['phases', tournoiId] })
      queryClient.invalidateQueries({ queryKey: ['avancement-phases'] })
      queryClient.invalidateQueries({ queryKey: ['suivi-deroule'] })
      queryClient.invalidateQueries({ queryKey: ['bareme-qualification', tournoiId] })
      queryClient.invalidateQueries({ queryKey: ['grain-validation', tournoiId] })
    },
  })
}

export function usePromouvoirFormat(tournoiId: number) {
  const invalider = useInvaliderFormats()
  return useMutation({
    mutationFn: (nom: string) => promouvoirFormat(tournoiId, nom),
    onSuccess: invalider,
  })
}

export function useImporterClubs() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (lignes: string) => importerClubs(lignes),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['clubs'] }),
  })
}
