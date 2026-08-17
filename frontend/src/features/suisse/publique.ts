// Adaptation d'une phase de **système suisse** vers le modèle neutre des formats sans arbre
// (E05US031, ADR-0089 §1) — logique pure, testée en node.
//
// Même partage que les poules : la feature est propriétaire de son DTO, `shared/rencontres/` ne
// connaît que le modèle de rendu.

import { libelleConflit } from '../../shared/rencontres/modele'
import type {
  ArcherPublic,
  ColonneClassement,
  FormatPublic,
  LigneClassement,
  RencontreVue,
  TourVue,
} from '../../shared/rencontres/modele'
import type { EtatSuissePublique, RencontreSuissePublique, RondePublique } from './api'
import { motDeLaFin } from './presentation'

const COLONNES: ColonneClassement[] = [
  { cle: 'points', libelle: 'Pts', aide: 'Une victoire vaut 1 point, un nul un demi-point.' },
  {
    cle: 'buchholz',
    libelle: 'Buchholz',
    aide: 'Somme des points des adversaires rencontrés : à points égaux, celui qui a affronté plus fort passe devant.',
  },
]

/** Rend en clair un total stocké en **demi-points doublés** : 3 → « 1½ », 2 → « 1 », 1 → « ½ ».
 *
 * ⚠️ **Le doublement est une décision du domaine, pas un détail d'encodage.** Une victoire vaut 2 et
 * un nul 1 pour éviter le flottant, dont les égalités approchées sont exactement ce sur quoi un
 * départage ne doit pas reposer. C'est donc à l'affichage de rendre la moitié — et **ici** plutôt
 * que dans le JSX, parce que c'est la seule forme qu'un test puisse exercer.
 *
 * Le même calcul vaut pour le Buchholz, qui somme des points de même unité.
 */
export function enDemiPoints(double: number): string {
  const entier = Math.floor(double / 2)
  const demi = double % 2 === 1
  if (!demi) return String(entier)
  return entier === 0 ? '½' : `${entier}½`
}

function versRencontre(rencontre: RencontreSuissePublique): RencontreVue {
  return {
    numero: rencontre.numero,
    haut: rencontre.haut,
    bas: rencontre.bas,
    couloirs: rencontre.couloirs,
    points_haut: rencontre.points_haut,
    points_bas: rencontre.points_bas,
    vainqueur:
      rencontre.vainqueur === 'haut' || rencontre.vainqueur === 'bas' ? rencontre.vainqueur : null,
    termine: rencontre.termine,
    validee: rencontre.validee,
    bloquee: rencontre.desynchronisee,
  }
}

function versTour(ronde: RondePublique): TourVue {
  return {
    libelle: `Ronde ${ronde.numero}`,
    rencontres: [...ronde.rencontres].sort((a, b) => a.numero - b.numero).map(versRencontre),
    // Le **bye** : sur un effectif impair, un archer est exempt à chaque ronde et marque comme s'il
    // avait gagné. C'est une propriété de la ronde, jamais une rencontre sans adversaire.
    exempt: ronde.bye,
    // `close` est ce dont l'écran a besoin pour dire pourquoi la ronde suivante n'est pas là : le
    // moteur refuse d'apparier par-dessus une ronde en cours. Une ronde ouverte n'est pas une
    // anomalie, c'est le régime normal d'une ronde en cours de saisie.
    clos: ronde.close,
  }
}

/** Les noms, relevés sur les **rencontres et les byes** — le classement ne porte que des `archer_id`.
 *
 * ⚠️ C'est la différence structurelle avec les poules, dont chaque bloc porte ses `membres`. Un
 * suisse n'a pas de liste de participants dans son état public : le seul endroit où un nom existe
 * est l'appariement. Un archer qui n'aurait jamais été apparié ni exempt resterait donc sans nom —
 * cas impossible en pratique (la ronde 1 apparie tout le monde), mais qui justifie le repli.
 */
function nomsDe(etat: EtatSuissePublique): Map<number, ArcherPublic> {
  const noms = new Map<number, ArcherPublic>()
  for (const ronde of etat.rondes) {
    for (const rencontre of ronde.rencontres) {
      for (const qui of [rencontre.haut, rencontre.bas]) {
        if (qui !== null) noms.set(qui.archer_id, qui)
      }
    }
    if (ronde.bye !== null) noms.set(ronde.bye.archer_id, ronde.bye)
  }
  return noms
}

function classementDe(etat: EtatSuissePublique): LigneClassement[] {
  const noms = nomsDe(etat)
  return etat.classement.map((rang) => {
    const qui = noms.get(rang.archer_id)
    return {
      rang: rang.rang,
      archer_id: rang.archer_id,
      nom: qui === undefined ? 'Archer' : `${qui.prenom} ${qui.nom}`.trim(),
      valeurs: [enDemiPoints(rang.points), enDemiPoints(rang.buchholz)],
      ex_aequo: rang.ex_aequo,
    }
  })
}

/** Ce que l'écran public a à dire **sous** les rondes.
 *
 * ⚠️ **Les rondes dues sont `min(nb_rondes, rondes_maximales)`, jamais `nb_rondes` seul.**
 * `nb_rondes` est le **réglage** (5 par défaut) ; `rondes_maximales` est ce que l'effectif permet
 * réellement — à 4 archers, 3. Comparer au réglage affichait « Ronde 3 sur 5 — l'appariement de la
 * suivante est imminent » **en permanence** sur une phase finie, pour une ronde qui n'arriverait
 * jamais. L'écran scoreur faisait déjà ce `Math.min` (`SaisieSuisse`) ; le calcul se délègue donc à
 * `motDeLaFin`, qui traite les trois états — dont « se taire », le seul juste quand la dernière
 * ronde due est en cours.
 *
 * ⚠️ **Zéro ronde n'est pas « ronde 0 »** : le serveur rend une photo vide sous deux participants
 * (l'état nominal du matin, ou une source amont qui n'a pas encore prélevé). Comme le suisse
 * fabrique **toujours** un bloc, le vide générique de `VueRencontres` est inatteignable ici : sans
 * ce cas, l'écran affichait « Ronde 0 sur 5 — l'appariement de la suivante est imminent ».
 */
function notesDe(etat: EtatSuissePublique): string[] {
  if (etat.rondes.length === 0) {
    return [
      'Cette phase n’a pas encore de participants : aucune ronde n’est appariée pour le moment.',
    ]
  }
  const dues = Math.min(etat.nb_rondes, etat.rondes_maximales)
  // `motDeLaFin` lit la **dernière** du tableau : on la lui donne triée, l'ordre du DTO n'étant
  // garanti nulle part.
  const triees = [...etat.rondes].sort((a, b) => a.numero - b.numero)
  const mot = motDeLaFin(triees, dues)
  if (mot !== null && mot.etat === 'fini') {
    return [`Les ${dues} rondes ont été tirées : le classement ci-dessous est définitif.`]
  }
  // ⚠️ **La ronde suivante n'apparaît qu'une fois la précédente close** : on le **dit** au lieu de
  // laisser un blanc que le spectateur lira comme une panne. C'est le CA d'E05US030 côté scoreur,
  // et il vaut ici pour la même raison.
  if (mot !== null) {
    return [
      `Ronde ${mot.courante} sur ${dues} — la ronde ${mot.suivante} sera appariée quand toutes les rencontres de celle-ci seront validées.`,
    ]
  }
  // `motDeLaFin` rend `null` dans deux cas, et un seul mérite un mot : une ronde **close** alors
  // qu'il en reste à tirer — l'appariement de la suivante n'a pas encore été fait. On le constate
  // sans rien promettre : « imminent » était un engagement que rien ici ne tient, le reproche fait
  // au même endroit à `PhaseSansVue`. L'autre cas (la dernière ronde due est en cours) reste muet,
  // se taire y étant la seule réponse juste.
  const derniere = triees.at(-1)
  if (derniere !== undefined && derniere.close && triees.length < dues) {
    return [`Ronde ${triees.length} sur ${dues} tirée — la suivante n’est pas encore appariée.`]
  }
  return []
}

/** Une phase de système suisse, prête pour la vue commune.
 *
 * **Un seul bloc**, sans titre : un suisse apparie tout le plateau d'un coup, il n'y a pas de groupe
 * à distinguer. Coiffer l'unique plateau d'un titre « Plateau 1 » coûterait une ligne sur 360 px
 * sans rien apprendre.
 */
export function formatPublicDuSuisse(etat: EtatSuissePublique): FormatPublic {
  return {
    blocs: [
      {
        cle: `suisse-${etat.phase_id}`,
        titre: null,
        tours: [...etat.rondes].sort((a, b) => a.numero - b.numero).map(versTour),
        colonnes: COLONNES,
        classement: classementDe(etat),
        notes: notesDe(etat),
      },
    ],
    // Le plateau du suisse est unique : le préfixer d'un numéro de groupe n'apprendrait rien.
    conflits: etat.conflits.map((c) => libelleConflit(c.raison)),
  }
}
