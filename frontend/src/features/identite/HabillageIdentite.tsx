// L'identité d'un tournoi **posée sur une surface** (E16US006, absorbe E01US016).
//
// ⚠️ **Portée : le public et l'écran de salle, jamais l'admin ni la saisie** (`D-27`). Tenu par le
// **montage** et non par une condition : ce composant n'est monté que dans `EcranSalle` et les vues
// publiques — un `if` aurait été un endroit de plus où se tromper. ⚠️ **Une balise `<style>` et non
// un `style={{...}}`** : les jetons sont définis **trois fois** dans `index.css` (`D-26`), et un
// style en ligne obligerait à lire le thème en JavaScript. On émet les trois déclinaisons, portées
// par un **attribut** plutôt que par `:root`, ce qui les scope à la surface habillée.

import { useIdentite } from './hooks'
import type { EmplacementLogo } from './api'
import { empreinteDuLogo, urlDuLogo } from './api'
import { cssDesJetons } from './jetons'
import './identite.css'

/**
 * Habille une surface avec l'identité d'un tournoi.
 *
 * Rend ses enfants **immédiatement**, sans attendre la réponse : tant que l'identité n'est pas
 * chargée, la surface porte simplement les jetons de la charte du club, qui sont déjà les bons par
 * défaut. Faire attendre l'écran de salle pour une question de couleur serait un écran noir sur un
 * vidéoprojecteur, ce qu'aucun CA ne demande.
 */
export function HabillageIdentite({
  tournoiId,
  children,
}: {
  tournoiId: number
  children: React.ReactNode
}) {
  const identite = useIdentite(tournoiId)
  const marqueur = `identite-${tournoiId}`

  return (
    <div data-identite={marqueur} className="habillage-identite">
      {identite.data !== undefined && <style>{cssDesJetons(marqueur, identite.data)}</style>}
      {children}
    </div>
  )
}

/**
 * Le logo d'un emplacement, ou **rien** s'il n'a pas été déposé.
 *
 * Les deux logos sont facultatifs (A05) : l'absence n'est pas un vide à combler par un cadre gris.
 * Rendu en `<img>` et non en fond CSS — un logo **est** du contenu, il a donc droit à un texte
 * alternatif —, ce qui neutralise en outre les scripts d'un SVG : troisième barrière après le refus
 * au dépôt et les en-têtes de la route.
 */
export function LogoDuTournoi({
  tournoiId,
  emplacement,
  className,
  decoratif = false,
}: {
  tournoiId: number
  emplacement: EmplacementLogo
  className?: string
  /**
   * `true` quand le logo est posé **à l'intérieur** d'un élément qui porte déjà le nom du tournoi.
   *
   * Un `alt` s'agrège au nom accessible de son conteneur : deux logos dans un `<h2>` faisaient
   * annoncer « Logo du tournoi Logo du club organisateur Challenge des Champions » au lecteur
   * d'écran (relevé en revue). L'information est alors **déjà dite** juste à côté, le logo n'est
   * que sa marque visuelle — c'est la définition d'une image décorative, donc `alt=""`.
   */
  decoratif?: boolean
}) {
  const identite = useIdentite(tournoiId)
  const empreinte =
    identite.data === undefined ? undefined : empreinteDuLogo(identite.data, emplacement)
  if (empreinte === undefined) return null

  return (
    <img
      className={className ?? 'logo-tournoi'}
      src={urlDuLogo(tournoiId, emplacement, empreinte)}
      alt={
        decoratif ? '' : emplacement === 'club' ? 'Logo du club organisateur' : 'Logo du tournoi'
      }
    />
  )
}
