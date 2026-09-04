// Mise en mots du palmarès (E06US004) — fonctions **pures**, testées à part de React.
//
// Trois règles, non cosmétiques. **Aucun rang inventé** : une fourchette s'affiche « 5ᵉ-8ᵉ » telle
// quelle, choisir un chiffre ferait dire à l'écran ce que la compétition n'a pas décidé (ADR-0065).
// **L'origine se dit** : « 9ᵉ » est ambigu, le préciser (« qualification ») évite de laisser croire
// à une élimination en duel. **Ce qui n'est pas décidé se nomme** : un podium vide dit « en cours
// », un blanc passerait pour une panne d'affichage sur un écran projeté.

import type { ClassementClubs, LignePalmares, Podium, PorteePodium } from './api'

const MEDAILLES: Record<number, string> = { 1: 'Or', 2: 'Argent', 3: 'Bronze' }

// Les libellés des portées, pour dire **sur quoi** le décompte des clubs repose. Servi puis jamais
// lu, `portees_comptees` ne tenait pas la promesse de son propre commentaire (relevé en revue, axe
// D) — et c'est l'information qui désamorce la surprise du double comptage : « Or : 2 » pour un club
// à un archer s'explique dès qu'on lit « Compté sur : Toutes catégories · Par catégorie ».
const PORTEES: Record<string, string> = {
  scratch: 'Toutes catégories',
  categorie: 'Par catégorie',
  club: 'Par club',
}

export function baseDuDecompte(portees: PorteePodium[]): string {
  return portees.map((portee) => PORTEES[portee] ?? portee).join(' · ')
}

// « 3ᵉ », « 5ᵉ-8ᵉ » ou « — » (hors classement). L'exposant ordinal suit l'usage français : « 1ᵉʳ »
// au premier rang, « ᵉ » ensuite.
export function rang(minimum: number | null, maximum: number | null): string {
  if (minimum === null || maximum === null) return '—'
  if (minimum === maximum) return ordinal(minimum)
  // Les **deux** bornes passent par `ordinal` : « 1ᵉ-2ᵉ » au lieu de « 1ᵉʳ-2ᵉ » était
  // le cas le plus visible du palmarès (les deux finalistes, en tête de liste), et le
  // test ne couvrait que `rang(5, 8)` — la seule fourchette dont la borne basse n'est
  // pas 1. Relevé par trois axes de revue.
  return `${ordinal(minimum)}-${ordinal(maximum)}`
}

export function ordinal(valeur: number): string {
  return valeur === 1 ? '1ᵉʳ' : `${valeur}ᵉ`
}

// La médaille d'un rang de podium — vide au-delà du bronze : ces places figurent au podium (la
// petite finale a décerné la 4ᵉ) mais ne reçoivent rien.
export function medaille(rangDansLaPortee: number | null): string {
  return rangDansLaPortee === null ? '' : (MEDAILLES[rangDansLaPortee] ?? '')
}

// La **provenance** d'une place de podium. Le moteur ne monte qu'un seul tableau scratch, donc dans
// la plupart des catégories le bronze est rangé par la qualification faute d'un match qui départage.
// On l'affiche (l'amputer laissait la majorité des catégories sans médailles) mais on le **dit** :
// c'est la distinction entre le classement et le podium, rendue visible plutôt que tranchée en
// supprimant des lignes.
export function provenance(ligne: LignePalmares): string | null {
  return ligne.decerne ? null : 'au classement'
}

// Ce qu'on écrit sous le rang d'une ligne. `null` quand il n'y a rien à ajouter : le cas normal
// d'un rang décerné en duel, où répéter « duels » serait du bruit sur 120 lignes.
export function detail(ligne: LignePalmares): string | null {
  if (ligne.statut === 'disqualifie') return 'Disqualifié'
  if (ligne.statut === 'abandon') return 'Abandon'
  if (ligne.origine === 'qualification') return 'Qualification'
  // ⚠️ « Reste à tirer » et non « à départager » : *départager* est le vocabulaire du
  // **barrage** (E06US003). Dire « à départager » à deux finalistes annonce au public
  // qu'une règle va décider, alors que c'est la finale — et c'est l'inverse pour les
  // quatre battus 5ᵉ-8ᵉ, que plus aucun match ne séparera. Les deux se présentaient
  // sous le même libellé faute d'exposer `en_lice` (relevé en revue, trois axes).
  if (ligne.en_lice) return 'Reste à tirer'
  if (ligne.rang_min !== ligne.rang_max) return 'Ex æquo'
  if (!ligne.decerne) return 'Départagé au classement'
  return null
}

// L'état d'un bloc de podium quand il n'est pas complet.
//
// ⚠️ **`en_attente` distingue « pas encore » de « plus jamais »** (E16US014). La branche « plus
// jamais » couvre DEUX causes — un ex æquo que rien ne départagera, et un groupe dont aucun archer
// n'est entré au tableau (cas **typique** de la portée club, `DETTE-028`) — d'où une formulation
// vraie des deux : « aucun duel n'a départagé ». Dire « ces archers sont ex æquo » était faux pour
// des archers aux rangs de qualification tous distincts (relevé par trois axes).
export function etatPodium(podium: Podium, profondeur: number): string | null {
  if (podium.places.length === 0) {
    return podium.en_attente
      ? 'Podium en cours — aucune place décernée.'
      : 'Aucune place décernée — aucun duel n’a départagé ce groupe.'
  }
  // Comparé à l'**effectif du groupe**, pas à la constante 3 : un groupe de deux archers (courant
  // en salle — Benjamine, Cadet Femme…) a un podium complet à deux noms, et affichait « podium
  // partiel » à perpétuité, tournoi terminé compris (relevé en revue, axes B et C1).
  //
  // ⚠️ `profondeur` entre au minimum **sans remplacer le 3** (E16US014) : le seuil reste celui des
  // **médailles**, pas des places affichées — sinon le réglage par défaut (4 places) ferait dire
  // « partiel » à tout podium complet de trois médaillés, une régression sur tous les tournois.
  const complet = Math.min(3, profondeur, podium.effectif)
  if (podium.places.length < complet) {
    return podium.en_attente
      ? 'Podium partiel — les finales ne sont pas toutes tirées.'
      : 'Podium partiel — aucun duel n’a départagé les places restantes.'
  }
  return null
}

export const nomComplet = (ligne: LignePalmares) => `${ligne.prenom} ${ligne.nom}`.trim()

// L'état du classement des clubs (E16US017) quand il n'y a rien à mettre dans la table — ou une
// réserve à porter au-dessus.
//
// ⚠️ **Les trois cas ne se confondent pas.** « Aucune base » vient du **réglage** (seuls des
// podiums internes aux clubs sont décernés) et ne se corrigera pas en attendant ; « aucun club »
// vient de la population ; « provisoire » vient du tournoi, et se lèvera tout seul. Les rendre
// sous un même blanc renverrait l'organisateur vérifier le mauvais écran.
export function etatClassementClubs(classement: ClassementClubs): string | null {
  // Le tournoi ne récompense rien : la section entière ne se rend pas (cf. `VuePalmares`).
  if (classement.portees_reglees.length === 0) return null
  if (classement.portees_comptees.length === 0)
    return 'Aucun classement des clubs — les podiums réglés récompensent à l’intérieur de chaque club, ils ne les comparent pas entre eux.'
  // ⚠️ Une phrase pour **trois** causes, et c'est délibéré : aucun club inscrit, aucune médaille
  // encore décernée, ou des médailles toutes revenues à des archers sans club. Elle est vraie des
  // trois, là où « le classement démarrera aux finales » serait faux de la première.
  // ⚠️ « encore » **seulement si ça peut changer** (relevé en revue, axe D) : sur un tournoi
  // sans phase à duels, il n'y en aura jamais, et l'adverbe promet une suite qui ne vient pas.
  if (classement.lignes.length === 0)
    return classement.provisoire
      ? 'Aucun club n’a encore de médaille.'
      : 'Aucun club n’a de médaille.'
  if (classement.provisoire) return 'Décompte provisoire — des podiums restent à décerner.'
  return null
}
