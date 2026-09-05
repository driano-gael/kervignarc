// Construction de la data URL d'une image SVG chargée en blob authentifié (E11US008, E16US015).
//
// ⚠️ **Ne pas dupliquer cette fonction par feature** : c'est de l'échappement. `encodeURIComponent`
// couvre tout le contenu (`#`, `&`, espaces, `%`…), de sorte qu'aucun caractère du SVG ne peut
// refermer ni détourner le contexte de la data URL. Deux copies, c'est une copie qui dérive.
// Partagée depuis E16US015 (2ᵉ appelant : le QR d'un scoreur).

export function svgEnDataUrl(svg: string): string {
  return `data:image/svg+xml,${encodeURIComponent(svg)}`
}
