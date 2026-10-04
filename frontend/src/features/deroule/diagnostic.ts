// Ce que l'écran dit du diagnostic serveur (E01US024) — logique pure, aucun React. Le diagnostic
// lui-même reste serveur (cf. l'en-tête de `Deroule.tsx`) : ici, on ne décide que de son affichage.

import {
  LIBELLE_TYPE,
  TYPES_SIGNALES_EN_ECART,
  type TypePhase,
} from '../../shared/phases/catalogue'
import type { Anomalie, Diagnostic } from './api'

export type ConstatEffectifMinimum =
  | { regime: 'information'; minimum: number }
  | { regime: 'insuffisant'; minimum: number; effectif: number }

export function constatEffectifMinimum(diagnostic: Diagnostic): ConstatEffectifMinimum | null {
  const minimum = diagnostic.effectif_minimum
  // 1 = « aucune exigence » : tout déroulé accueille au moins un archer. L'afficher ferait passer
  // une trivialité pour une contrainte.
  if (minimum <= 1) return null
  if (diagnostic.effectif !== null && diagnostic.effectif < minimum) {
    return { regime: 'insuffisant', minimum, effectif: diagnostic.effectif }
  }
  return { regime: 'information', minimum }
}

// Les types que le moteur ne sait **pas encore** exécuter — domiciliés au catalogue partagé et
// écrits en **négatif** : un oubli y coûte un avertissement de trop, jamais un de moins.
const EN_ECART = new Set<TypePhase>(TYPES_SIGNALES_EN_ECART)

export interface MotifsDeReserve {
  prelevementInerte: boolean
  libellesEnEcart: string[]
}

export function motifsDeReserve(diagnostic: Diagnostic): MotifsDeReserve | null {
  // ⚠️ **Reformulée, pas supprimée** (E05US020, ADR-0068) : le moteur lit les prélèvements **par
  // rangs**, restent inertes « le reste » et « les gagnants/perdants du tour N » (DETTE-033). La
  // réserve ne s'affiche donc que si l'un d'eux est déclaré : continuer à l'afficher aurait fait
  // douter d'un déroulé exact, la retirer aurait laissé croire que tout est honoré. ⚠️ Deux causes
  // distinctes d'inexactitude, que l'ancienne condition couvrait **par accident** — ne garder que
  // la première aurait fait disparaître l'avertissement d'un « qualification → poules », que le
  // moteur ne sait toujours pas dérouler.
  const prelevementInerte = diagnostic.blocs.some((bloc) =>
    bloc.entrees.some((flux) => flux.nature !== 'rangs'),
  )
  // Les types **réellement** en cause, et non une liste figée. Le bandeau nommait « suisse,
  // colline, Big Shoot Off » en dur alors que `TYPES_SIGNALES_EN_ECART` en compte cinq : composer
  // une phase `placement` ou `barrage` allumait donc un avertissement qui désignait trois formats
  // que l'organisateur n'avait pas utilisés (correctif de revue). Le CA fait précisément de la
  // justesse de ce signal son exigence.
  const typesEnEcart = [...new Set(diagnostic.blocs.map((bloc) => bloc.type))].filter((type) =>
    EN_ECART.has(type),
  )
  if (!prelevementInerte && typesEnEcart.length === 0) return null
  return { prelevementInerte, libellesEnEcart: typesEnEcart.map((type) => LIBELLE_TYPE[type]) }
}

// `DV-03` : jamais la couleur seule — une pastille et un mot portent le sens.
export function intituleAnomalie(anomalie: Anomalie): { pastille: string; intitule: string } {
  const bloquante = anomalie.gravite === 'bloquante'
  const localisation = anomalie.ordre === null ? '' : ` — phase ${anomalie.ordre}`
  return {
    pastille: bloquante ? '●' : '▲',
    intitule: `${bloquante ? 'Bloquant' : 'À vérifier'}${localisation}`,
  }
}
