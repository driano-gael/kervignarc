// Dérivation **pure** du verdict d'un jalon (E16US012) — isolée du rendu React pour être testée en
// node, comme `completude/presentation.ts` ou `supervision/etat.ts`.
//
// **Pourquoi un verdict écrit, et pas seulement la liste.** Le CA dit que l'écran répond à *une
// question binaire*. Une liste d'états y répond implicitement — il faut la lire en entier et savoir
// lesquelles bloquent. La phrase, elle, répond tout de suite ; la liste dit ensuite *pourquoi*.

export type TonVerdict = 'ok' | 'alerte'

export interface Verdict {
  ton: TonVerdict
  texte: string
}

// Les **trois** cas, et pas deux : `pret` seul ne suffit pas à écrire la phrase.
//
// C'est l'asymétrie de la famille (ADR-0096). « Il manque quelque chose » se dit différemment
// selon que le serveur **refusera** (démarrer : `TournoiSansDepart`,
// `EffectifInsuffisantPourDemarrer`) ou **laissera passer** (terminer, qui n'a aucune garde dure).
// Annoncer un refus là où l'appli accepte ferait un écran plus sévère que le produit ; annoncer
// « allez-y » là où le serveur refuse enverrait l'organisateur au 409, le jour J, devant la salle.
//
// Le texte reste **générique** : il ne nomme pas le verbe du jalon, pour qu'`archiver` et
// `exporter` se branchent sans le réécrire — c'est le titre de l'écran qui porte le verbe.
export function verdict(pret: boolean, bloquant: boolean): Verdict {
  if (pret) return { ton: 'ok', texte: 'Oui — rien ne s’y oppose.' }
  if (bloquant) {
    return { ton: 'alerte', texte: 'Pas encore — ce qui manque ci-dessous sera refusé.' }
  }
  return {
    ton: 'alerte',
    texte: 'Il reste des choses à faire — l’application ne vous en empêchera pas.',
  }
}
