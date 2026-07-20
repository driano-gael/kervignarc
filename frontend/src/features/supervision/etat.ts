// Dérivation pure de l'affichage d'un poste dans la console de supervision (E12US001, ADR-0038).
//
// Isolée du rendu React pour être **testée** en node (comme `shared/realtime/indicateur.ts`). Rappel
// de l'arbitrage (ADR-0038, story E12US001) : un poste **hors ligne** se signale en **ambre** (token
// sémantique `--warn`), **jamais** en rouge — sur l'anthracite de la charte le rouge ne contraste pas
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
// rattaché, ou rattaché sans départ courant → `avancement` nul côté serveur), ou qualification pas
// encore configurée (`nb_volees === 0`) — on n'affiche pas « volée 0/0 ».
export function avancementLibelle(
  avancement: { volee_courante: number; nb_volees: number } | null,
): string {
  if (avancement === null || avancement.nb_volees === 0) return '—'
  return `volée ${avancement.volee_courante}/${avancement.nb_volees}`
}
