// L'identité d'un tournoi **posée sur une surface** (E16US006, absorbe E01US016).
//
// ⚠️ **Portée : le public et l'écran de salle, jamais l'admin ni la saisie** (`D-27`). Ce n'est pas
// tenu par une condition mais par le **montage** : ce composant n'est monté que dans `EcranSalle` et
// dans les vues publiques d'un tournoi. Un `if` aurait été un endroit de plus où se tromper ; une
// coquille qui ne l'appelle pas ne peut pas le porter par accident. La raison, elle, est écrite dans
// le CDC : « le jour J, un bénévole n'a pas le temps de réapprendre des repères visuels ».
//
// ⚠️ **Pourquoi une balise `<style>` et pas un `style={{...}}` en ligne.** Les jetons de marque sont
// définis **trois fois** dans `index.css` — sombre, clair, et « Système » sous `prefers-color-scheme`
// (`D-26`). Un style en ligne ne pose qu'une valeur : il faudrait donc lire le thème en JavaScript,
// et écouter ses changements. La charte a déjà tranché ce dilemme pour elle-même, et sa raison vaut
// ici mot pour mot : « rendu en CSS et non en JS à dessein — la page suit alors le basculement de
// l'OS **en direct**, sans écouteur `matchMedia` à câbler ni à nettoyer ». On émet donc les trois
// mêmes déclinaisons, **portées par un attribut** plutôt que par `:root`, ce qui les scope à la
// surface habillée.

import { useIdentite } from './hooks'
import type { EmplacementLogo } from './api'
import { urlDuLogo } from './api'
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
 * Les deux logos sont facultatifs (« bien sûr cela reste optionnel », questionnaire A05) : l'absence
 * n'est pas un vide à combler par un cadre gris, c'est simplement un tournoi qui n'a pas de logo.
 *
 * Rendu en `<img>` et non en fond CSS : un logo **est** du contenu (il nomme la compétition), il a
 * donc droit à un texte alternatif. Le `<img>` neutralise par ailleurs les scripts d'un SVG — une
 * troisième barrière après le refus au dépôt et les en-têtes de la route.
 */
export function LogoDuTournoi({
  tournoiId,
  emplacement,
  className,
}: {
  tournoiId: number
  emplacement: EmplacementLogo
  className?: string
}) {
  const identite = useIdentite(tournoiId)
  if (identite.data === undefined || !identite.data.logos.includes(emplacement)) return null

  return (
    <img
      className={className ?? 'logo-tournoi'}
      src={urlDuLogo(tournoiId, emplacement, identite.dataUpdatedAt)}
      alt={emplacement === 'club' ? 'Logo du club organisateur' : 'Logo du tournoi'}
    />
  )
}
