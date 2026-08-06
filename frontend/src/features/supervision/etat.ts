// Dérivation pure de l'affichage d'un poste dans la console de supervision (E12US001, ADR-0038).
//
// Isolée du rendu React pour être **testée** en node (comme `shared/realtime/indicateur.ts`). Rappel
// de l'arbitrage (ADR-0038, story E12US001) : un poste **hors ligne** se signale en **ambre** (token
// sémantique `--danger` — nommé `--warn` jusqu'à E17US001, qui a fondu les deux alertes en une seule
// depuis que la charte est posée), **jamais** en rouge — sur l'anthracite de la charte le rouge ne contraste pas
// assez et ne signale rien (`DV-03`). Et toujours **couleur + pastille + texte**, jamais la couleur
// seule (le `libelle` porte l'information pour qui ne distingue pas les teintes).

export type EtatPoste = 'en_ligne' | 'hors_ligne' | 'non_rattache'

export interface AfficheEtat {
  classe: EtatPoste
  libelle: string
}

export function afficheEtat(etat: EtatPoste): AfficheEtat {
  switch (etat) {
    case 'en_ligne':
      return { classe: 'en_ligne', libelle: 'En ligne' }
    case 'hors_ligne':
      return { classe: 'hors_ligne', libelle: 'Hors ligne' }
    case 'non_rattache':
      return { classe: 'non_rattache', libelle: 'Non rattaché' }
  }
}

// Libellé d'avancement (« volée 8/12 »), ou tiret quand il n'a pas de sens : poste sans grille (non
// rattaché, ou rattaché sans départ courant → `avancement` nul côté serveur), qualification pas
// encore configurée (`nb_volees === 0`), ou cible sans **aucun** archer placé (`volee_courante === 0`,
// le serveur ne peut situer aucun rythme) — on n'affiche ni « volée 0/0 » ni « volée 0/12 ».
export function avancementLibelle(
  avancement: { volee_courante: number; nb_volees: number } | null,
): string {
  if (avancement === null || avancement.nb_volees === 0 || avancement.volee_courante === 0)
    return '—'
  return `volée ${avancement.volee_courante}/${avancement.nb_volees}`
}

export interface Avancement {
  volee_courante: number
  nb_volees: number
}

/** Y a-t-il un avancement **situable** ? Trois cas où la réponse est non, et ils viennent tous du
 *  serveur : pas de grille du tout, qualification non configurée, ou aucun archer placé. Extrait de
 *  `avancementLibelle` pour que la jauge et le libellé ne puissent pas diverger (E17US004). */
function situable(a: Avancement | null): a is Avancement {
  return a !== null && a.nb_volees !== 0 && a.volee_courante !== 0
}

/**
 * La volée en cours, en forme courte — le « v8 » de la tuile de la planche A13.
 *
 * Court **à dessein** : une tuile de 150 px vue parmi trente doit se lire d'un coup d'œil, pas se
 * déchiffrer. Le libellé long (« volée 8/12 ») reste celui du tableau, où il y a la place.
 */
export function voleeCourte(avancement: Avancement | null): string | null {
  return situable(avancement) ? `v${avancement.volee_courante}` : null
}

/**
 * La part de la grille déjà tirée, entre 0 et 1 — le remplissage de la jauge de la tuile.
 *
 * **Bornée volontairement à 1** : le serveur peut annoncer une volée courante au-delà du nombre de
 * volées (une reprise, une grille raccourcie en cours de route). Sans borne, la jauge déborderait de
 * sa piste — un défaut d'affichage pour une donnée qui, elle, n'est pas fausse.
 */
export function fractionAvancement(avancement: Avancement | null): number | null {
  if (!situable(avancement)) return null
  return Math.min(1, avancement.volee_courante / avancement.nb_volees)
}
