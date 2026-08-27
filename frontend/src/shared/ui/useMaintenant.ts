// Un **battement local** : « quelle heure est-il », re-rendu à intervalle régulier (E05US034).
//
// **Pourquoi un hook et pas `Date.now()` dans le rendu** : lire l'horloge pendant le rendu est une
// impureté que `react-hooks/purity` refuse à raison — le résultat changerait à chaque re-rendu
// fortuit. ⚠️ **Ce n'est pas un compteur incrémenté** : on **relit** l'horloge à chaque battement
// au lieu d'ajouter une seconde, car un onglet en arrière-plan voit ses minuteurs bridés et un
// compteur y accumulerait des minutes de dérive sur une journée.

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
