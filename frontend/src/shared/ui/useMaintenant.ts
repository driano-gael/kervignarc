// Un **battement local** : « quelle heure est-il », re-rendu à intervalle régulier (E05US034).
//
// **Pourquoi un hook et pas `Date.now()` dans le rendu.** Lire l'horloge pendant le rendu est une
// impureté — `react-hooks/purity` la refuse, et à raison : le résultat changerait à chaque re-rendu
// fortuit, sans qu'aucun état ne l'explique. Le hook rend l'instant **explicite** : c'est un état,
// il change quand le battement le dit, et React sait pourquoi il re-rend.
//
// ⚠️ **Ce n'est pas la même chose qu'un compteur incrémenté**, et la nuance est celle que
// `salle/rotation.ts` documente : on relit l'horloge à chaque battement au lieu d'ajouter une
// seconde. Un onglet en arrière-plan voit ses minuteurs bridés par le navigateur ; un compteur
// incrémenté y accumulerait une dérive de plusieurs minutes sur une journée de tournoi, alors qu'un
// `Date.now()` relu est juste **quel que soit** le nombre de battements manqués.

import { useEffect, useState } from 'react'

/**
 * L'instant courant en millisecondes, rafraîchi toutes les `intervalleMs`.
 *
 * Choisir l'intervalle en fonction du **grain affiché**, pas de la précision voulue : une durée
 * rendue à la minute n'a pas besoin d'un battement à la seconde, qui ne ferait que multiplier les
 * re-rendus d'un écran qui reste ouvert huit heures.
 */
export function useMaintenant(intervalleMs: number): number {
  const [instant, setInstant] = useState(() => Date.now())
  useEffect(() => {
    const battement = window.setInterval(() => setInstant(Date.now()), intervalleMs)
    return () => window.clearInterval(battement)
  }, [intervalleMs])
  return instant
}
