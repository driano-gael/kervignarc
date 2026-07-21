import { ErreurApi } from '../api/client'

/**
 * Affichage standard d'une erreur de features — **point de vérité unique** (E00US013, DETTE-004).
 *
 * Auparavant recopié à l'identique dans chaque feature ; centralisé ici pour qu'un changement de
 * rendu (couleur, ton, accessibilité) se fasse **une fois**. En particulier, le token d'alerte doit
 * devenir **ambre** (`DV-03`, CDC design) au thème sombre : il ne doit s'appliquer qu'à **un** endroit.
 *
 * Une `ErreurApi` porte un message déjà destiné à l'utilisateur (mappé à la frontière API) ; toute
 * autre erreur reste un imprévu technique et se réduit à un message générique — jamais de détail
 * interne à l'écran.
 */
export function MessageErreur({ erreur }: { erreur: Error | null }) {
  if (erreur === null) return null
  const message = erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
  return (
    <p className="carte__etat carte__etat--erreur" role="alert">
      {message}
    </p>
  )
}
