// Retarde une valeur qui change à chaque frappe (E16US010).
//
// ⚠️ **Ce n'est pas du confort.** La recherche transverse est passée d'un filtrage local à une
// requête serveur : sans retard, taper « leveque » part en sept requêtes, dont chacune relit
// **trois référentiels entiers** côté serveur (`DETTE-092`). Le retard divise ce coût par cinq
// sans rien changer à l'ergonomie. Quelques lignes maison plutôt qu'une dépendance (règle 11).

import { useEffect, useState } from 'react'

export function useValeurRetardee<T>(valeur: T, delaiMs = 250): T {
  const [retardee, setRetardee] = useState(valeur)
  useEffect(() => {
    const minuteur = setTimeout(() => setRetardee(valeur), delaiMs)
    return () => clearTimeout(minuteur)
  }, [valeur, delaiMs])
  return retardee
}
