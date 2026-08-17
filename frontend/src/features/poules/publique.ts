// Adaptation d'une phase de **poules** vers le modèle neutre des formats sans arbre (E05US031,
// ADR-0089 §1) — logique pure, testée en node.
//
// **Pourquoi ici et pas dans `shared/`** : cette feature est propriétaire de son DTO. Faire entrer
// `EtatPoules` dans `shared/rencontres/` ferait importer `shared/ → features/`, la seule inversion
// que le front n'ait jamais tolérée. Le partage porte sur le **modèle de rendu**, pas sur les
// contrats de format.

import { libelleConflit } from '../../shared/rencontres/modele'
import type {
  ArcherPublic,
  BlocRencontres,
  ColonneClassement,
  FormatPublic,
  LigneClassement,
  RencontreVue,
  TourVue,
} from '../../shared/rencontres/modele'
import type { EtatPoules, PoulePublique, RencontrePublique } from './api'

/** Les cinq critères de départage du §10.1, dans l'ordre où le domaine les applique.
 *
 * ⚠️ **L'ordre des colonnes n'est pas cosmétique** : c'est lui qui rend le classement *traçable*.
 * Un spectateur qui voit deux archers à égalité de points doit pouvoir lire, de gauche à droite, ce
 * qui les a départagés. Les réordonner « pour la lisibilité » ferait mentir la lecture.
 */
const COLONNES: ColonneClassement[] = [
  { cle: 'points_match', libelle: 'Pts', aide: 'Points de match : 2 par victoire, 1 par nul.' },
  { cle: 'diff_sets', libelle: 'Δ sets', aide: 'Différence de sets gagnés et perdus.' },
  { cle: 'diff_score', libelle: 'Δ score', aide: 'Différence de points marqués et encaissés.' },
  { cle: 'nb_dix', libelle: '10', aide: 'Nombre de 10 marqués.' },
  { cle: 'nb_neuf', libelle: '9', aide: 'Nombre de 9 marqués.' },
]

function versRencontre(rencontre: RencontrePublique): RencontreVue {
  return {
    numero: rencontre.numero,
    haut: rencontre.haut,
    bas: rencontre.bas,
    couloirs: rencontre.couloirs,
    points_haut: rencontre.points_haut,
    points_bas: rencontre.points_bas,
    // Le serveur rend `'haut'`, `'bas'` ou `null` (`Cote.value`). On ne l'élargit pas : une chaîne
    // inattendue vaut « pas de vainqueur », ce qui est la lecture prudente — annoncer un gagnant
    // sur une valeur qu'on ne comprend pas serait le seul choix réellement faux.
    vainqueur:
      rencontre.vainqueur === 'haut' || rencontre.vainqueur === 'bas' ? rencontre.vainqueur : null,
    termine: rencontre.termine,
    validee: rencontre.validee,
    bloquee: rencontre.desynchronisee,
  }
}

/** Les rencontres d'une poule, groupées par **tour** — le round-robin se lit tour par tour.
 *
 * Les tours sont rendus **tous**, y compris ceux déjà joués : c'est le CA « l'historique des tours
 * reste lisible » (cadrage du 17/08/2026). Un spectateur qui arrive au tour 4 doit pouvoir lire les
 * trois premiers.
 */
function toursDe(poule: PoulePublique): TourVue[] {
  const parTour = new Map<number, RencontrePublique[]>()
  for (const rencontre of poule.rencontres) {
    const existantes = parTour.get(rencontre.tour)
    if (existantes === undefined) parTour.set(rencontre.tour, [rencontre])
    else existantes.push(rencontre)
  }
  return [...parTour.entries()]
    .sort(([a], [b]) => a - b)
    .map(([numero, rencontres]) => ({
      libelle: `Tour ${numero}`,
      rencontres: [...rencontres].sort((a, b) => a.numero - b.numero).map(versRencontre),
      // Une poule n'a pas de bye : le round-robin apparie tout le monde à chaque tour, et un
      // effectif impair se règle à la composition, pas au tour.
      exempt: null,
      // ⚠️ **`desynchronisee` compte comme close**, sans quoi le tour ne se clôt **jamais** : le
      // serveur refuse d'écrire sur une rencontre désynchronisée (la population a bougé sous un
      // score déjà saisi), donc elle ne sera jamais `validee`. Tant que la marque « en cours »
      // ornait *tous* les tours ouverts, le défaut passait inaperçu ; depuis qu'elle ne marque que
      // le **premier**, un tour bloqué la capte définitivement et le tour réellement tiré n'en
      // porte plus aucune. Relevé par l'axe adversarial à la 2ᵉ passe — la correction précédente
      // avait déplacé le défaut plutôt que de le créer.
      clos: rencontres.every((r) => r.validee || r.desynchronisee),
    }))
}

function classementDe(poule: PoulePublique): LigneClassement[] {
  const noms = new Map<number, ArcherPublic>(poule.membres.map((m) => [m.archer_id, m]))
  return poule.classement.map((rang) => {
    const qui = noms.get(rang.archer_id)
    return {
      rang: rang.rang,
      archer_id: rang.archer_id,
      // Le nom vient de la composition de la poule, jamais d'un cache client : un archer renommé
      // garde son suivi sans afficher un nom périmé.
      nom: qui === undefined ? 'Archer' : `${qui.prenom} ${qui.nom}`.trim(),
      valeurs: [
        String(rang.points_match),
        String(rang.diff_sets),
        String(rang.diff_score),
        String(rang.nb_dix),
        String(rang.nb_neuf),
      ],
      ex_aequo: rang.ex_aequo,
    }
  })
}

function notesDe(poule: PoulePublique): string[] {
  const notes: string[] = []
  if (poule.bloc === null) {
    notes.push('Le plan de cibles n’est pas encore posé : les couloirs de tir ne sont pas connus.')
  }
  // ⚠️ **Le barrage se dit, il ne se devine pas** (ADR-0083 §5). Sans cette ligne, le spectateur lit
  // deux archers au même rang et conclut à un bug d'affichage, alors que le départage est prévu et
  // se tirera au pas de tir.
  if (poule.barrage_requis) {
    notes.push('Des archers restent à égalité : un barrage les départagera.')
  }
  return notes
}

function versBloc(poule: PoulePublique): BlocRencontres {
  return {
    cle: `poule-${poule.numero}`,
    titre: `Poule ${poule.numero}`,
    tours: toursDe(poule),
    colonnes: COLONNES,
    classement: classementDe(poule),
    notes: notesDe(poule),
  }
}

/** Une phase de poules, prête pour la vue commune. */
export function formatPublicDesPoules(etat: EtatPoules): FormatPublic {
  return {
    blocs: [...etat.poules].sort((a, b) => a.numero - b.numero).map(versBloc),
    conflits: etat.conflits.map((c) => libelleConflit(c.raison, `Poule ${c.poule}`)),
  }
}
