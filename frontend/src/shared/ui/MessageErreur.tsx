import { texteErreur } from './texteErreur'

/**
 * Affichage standard d'une erreur de features — **point de vérité unique** (E00US013, DETTE-004).
 *
 * Auparavant recopié à l'identique dans chaque feature : centralisé pour qu'un changement de rendu
 * se fasse **une fois** — en particulier le token d'alerte **ambre** (`DV-03`). Une `ErreurApi`
 * porte un message déjà destiné à l'utilisateur ; toute autre erreur se réduit à un message
 * générique, jamais de détail interne à l'écran.
 */
export function MessageErreur({ erreur }: { erreur: Error | null }) {
  if (erreur === null) return null
  const message = texteErreur(erreur)
  return (
    <p className="carte__etat carte__etat--erreur" role="alert">
      {message}
    </p>
  )
}
