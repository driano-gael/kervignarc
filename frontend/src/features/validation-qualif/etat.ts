// Logique pure du panneau de validation de qualification (E16US019) — aucun appel réseau ici.
//
// Ce que le scoreur doit lire d'une feuille avant d'agir : ce qui est validé, ce qui est rouvert,
// et — quand il annule — **ce que la confirmation doit nommer**. La règle d'annulation vit au
// serveur (`Serie.annuler_validation`, ADR-0109) ; ici on ne fait qu'en **rendre l'effet lisible**
// avant le geste, à partir du lot que le serveur expose.

import type { Serie, Volee } from '../saisie/api'

// Une volée « compte » dès qu'elle porte un validateur — y compris pendant une correction. C'est le
// découplage d'ADR-0109 vu du front : `verrouillee` ne suffit plus à savoir si le score est acquis.
export function estValidee(volee: Volee): boolean {
  return volee.validee_par !== null
}

// Les volées qu'une annulation sur `numero` va rouvrir : son **lot** de validation, exactement.
// Vide si la volée n'est pas annulable (pas validée, ou déjà en correction).
export function voleesQueLAnnulationRouvre(serie: Serie, numero: number): number[] {
  const cible = serie.volees.find((volee) => volee.numero === numero)
  if (cible === undefined || cible.en_correction || cible.lot_validation === null) return []
  return serie.volees
    .filter((volee) => volee.lot_validation === cible.lot_validation)
    .map((volee) => volee.numero)
}

// Le texte de l'avertissement : il **nomme** ce qui va être rouvert (CA « l'écran dit ce qu'il
// fait »), jamais un « êtes-vous sûr ? » qui ne dit rien.
export function avertissementAnnulation(serie: Serie, numero: number): string {
  const numeros = voleesQueLAnnulationRouvre(serie, numero)
  if (numeros.length === 0) return "Cette volée n'a pas de validation à annuler."
  const uneSeule = numeros.length === 1
  const sujet = uneSeule
    ? `La volée ${numeros[0]} redevient saisissable`
    : `Les volées ${numeros.join(', ')} redeviennent saisissables`
  return `${sujet} sur la tablette de la cible. Le score reste au classement jusqu'à la ressaisie.`
}

// L'étiquette d'état d'une volée, telle qu'elle se lit dans la liste.
export function etatVolee(volee: Volee): 'en_correction' | 'validee' | 'en_cours' {
  if (volee.en_correction) return 'en_correction'
  return estValidee(volee) ? 'validee' : 'en_cours'
}

// Y a-t-il quelque chose à valider ? Une volée saisie non validée, ou une correction à refermer —
// les deux se présentent au serveur de la même façon : une volée non verrouillée.
export function aValider(serie: Serie): boolean {
  return serie.volees.some((volee) => !volee.verrouillee)
}
