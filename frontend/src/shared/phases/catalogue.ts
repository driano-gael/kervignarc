// Le **catalogue des types de phase**, côté front : l'union, ses libellés, ses aides (E05US015,
// ADR-0062).
//
// **Pourquoi ce module existe** — DETTE-030 (`docs/dette.md`) constatait que l'union `TypePhase`
// vivait en **deux** exemplaires (`features/phases/api.ts`, `features/patrimoine/api.ts`), et les
// libellés en deux aussi (`Phases.tsx`, `patrimoine/format.ts`). Le registre l'assumait
// explicitement « **tant qu'il n'y en a que deux** — à une 3ᵉ, l'extraire dans un module partagé se
// justifiera ». E01US024 est cette 3ᵉ occurrence : l'écran de composition d'un déroulé nomme les
// mêmes types. On extrait donc, comme annoncé, plutôt que d'aggraver une dette listée
// (règle « Dette » du CLAUDE.md) — et sur **preuve dans le code d'aujourd'hui**, pas sur une
// évolution supposée.
//
// Les deux `api.ts` **ré-exportent** d'ici : aucun import existant ne casse, et il n'y a plus qu'un
// seul domicile à synchroniser avec l'enum `TypePhase` du backend.
//
// ⚠️ **Exhaustivité obligatoire.** Chaque table est un `Record<TypePhase, …>`, jamais un ternaire à
// repli : c'est un repli (`… : 'Placement'`) qui a fait afficher six types comme « Placement » sans
// que TypeScript bronche. Le `Record` rend l'oubli d'un type **non compilable** — la seule forme
// qui tienne face à une union destinée à s'élargir.

// Types de phase déclarables (ADR-0045 §2), catalogue peuplé par E05US015 (ADR-0062).
// Le repêchage et le handicap n'y figurent **pas** : ce sont des politiques (`routing`, `scoring`),
// pas des types — un type se justifie par une **structure**, pas par un réglage (ADR-0062 §1).
export type TypePhase =
  | 'qualification'
  | 'elimination_directe'
  | 'placement'
  | 'echauffement'
  | 'barrage'
  | 'poules'
  | 'big_shoot_off'
  | 'suisse'
  | 'colline'

// Comment un prélèvement puise dans la phase amont (E05US010, miroir de `NatureSource`).
export type NatureSource = 'rangs' | 'issue_de_tour' | 'reste'

// Le côté d'un tour dont on prélève (miroir de `IssueTour`).
export type IssueTour = 'gagnants' | 'perdants'

export const LIBELLE_TYPE: Record<TypePhase, string> = {
  qualification: 'Qualification',
  elimination_directe: 'Élimination directe',
  placement: 'Placement',
  echauffement: 'Échauffement',
  barrage: 'Barrage',
  poules: 'Poules',
  big_shoot_off: 'Big Shoot Off',
  suisse: 'Système suisse',
  colline: 'Colline (King of the Hill / Ladder)',
}

// Nomme un type de phase venu du serveur, avec repli sur la chaîne brute.
//
// ⚠️ **Dérogation explicite au ⚠️ d'en-tête** (précision de revue) : celui-ci interdit les replis
// **dans les tables**, parce qu'un `Record` à repli fait afficher six types comme « Placement ».
// `LIBELLE_TYPE` reste un `Record<TypePhase, string>` exhaustif — ajouter un type à l'union reste
// non compilable. Le repli ci-dessous ne s'arme que pour une chaîne **hors union**, ce qui ne peut
// venir que d'un serveur plus récent que ce bundle : ce n'est pas la même chose, et l'interdire
// reviendrait à afficher un blanc là où le nom technique renseigne encore.
//
// Le repli couvre un **déploiement décalé** : un backend plus récent peut connaître un type que ce
// bundle ignore (l'appli publique reste ouverte des heures sur un téléphone). Mieux vaut alors
// « 3. poules » que rien du tout.
//
// ⚠️ Le cast porte sur la **table**, pas sur la valeur (correctif de revue). Écrire
// `LIBELLE_TYPE[type as TypePhase] ?? type` affirmait qu'une chaîne serveur quelconque *est* un
// `TypePhase` : TS typait alors l'accès en `string` non nullable, rendant le `??` **mort pour le
// compilateur** alors qu'il est le seul filet réel à l'exécution — le genre de cast qui survit
// après qu'on ait retiré le repli.
//
// Son domicile est ici, sous `LIBELLE_TYPE` : deux features en avaient écrit une copie chacune.
export function nommerType(type: string): string {
  return (LIBELLE_TYPE as Record<string, string | undefined>)[type] ?? type
}

// Ce que chaque type fait, en une ligne : la moitié de ces formats est inconnue de l'organisateur
// qui ouvre l'écran, et un `<select>` de neuf entrées sans explication n'aide personne à choisir.
export const AIDE_TYPE: Record<TypePhase, string> = {
  qualification: 'Tir au cumul qui produit le classement de départ.',
  elimination_directe: 'Tableau à duels ; le perdant sort (petite finale comprise).',
  placement: 'Tableau qui classe tout le monde, du 1er au dernier.',
  echauffement: 'Sans point ni classement : occupe du temps et des cibles.',
  barrage: 'Départage des ex æquo à 1 flèche, avant de monter un tableau.',
  poules: 'Groupes en round-robin ; le classement de poule qualifie.',
  big_shoot_off: 'Finale à N archers : le plus faible sort à chaque manche.',
  suisse: 'Rondes vainqueurs contre vainqueurs, personne n’est éliminé.',
  colline: 'Défis entre voisins : le gagnant monte, le perdant descend.',
}

// Les types qui ne produisent **aucun classement** : on ne peut pas y prélever de rangs (le serveur
// le refuse). Miroir de `_TYPES_SANS_CLASSEMENT` côté domaine — le backend reste l'autorité, ceci
// évite juste d'offrir un choix qui mène à un 422 dont la consigne n'est pas réalisable à l'écran.
export const TYPES_SANS_CLASSEMENT: TypePhase[] = ['echauffement']

// Les types qui montent un **arbre de duels**, donc les seuls dont la profondeur de classement soit
// un réglage (E06US006). Miroir de `TYPES_EN_TABLEAU` côté domaine, même parti que ci-dessus : le
// backend refuse (422) une profondeur sur un autre type, l'écran évite simplement de la proposer.
export const TYPES_EN_TABLEAU: TypePhase[] = ['elimination_directe', 'placement']

// Jusqu'où une phase en tableau départage ses participants (E06US006, ADR-0070).
//
// `un_vers_n` joue **tous** les rangs (placement intégral) ; `top_n` s'arrête au `jusqu_au`-ième,
// les battus des tours antérieurs restant groupés sur leur fourchette. Le catalogue `depth` du
// serveur en compte un troisième (`aucun`) volontairement absent de la façade : c'est le contenu du
// type échauffement, pas un réglage de tableau.
//
// ⚠️ Domicilié ici et non dans une feature (corrigé en revue) : trois modules le consomment
// (`patrimoine/api.ts`, `phases/api.ts`, `shared/phases/ChoixProfondeur.tsx`), et le laisser dans
// `features/patrimoine` faisait importer `shared/ → features/` — la **seule** inversion de ce genre
// du front, sur le même seuil de 3 occurrences qui avait justifié l'extraction de ce fichier.
export interface Profondeur {
  nom: 'un_vers_n' | 'top_n'
  // Le rang d'arrêt — porté par `top_n` seulement. `null` sur `un_vers_n` : un classement intégral
  // ne s'arrête à aucun rang, et le serveur refuse (422) qu'on lui en donne un.
  jusqu_au: number | null
}

/** L'ordre d'affichage du catalogue dans un `<select>` — le plus courant d'abord. */
export const TOUS_LES_TYPES: TypePhase[] = [
  'qualification',
  'elimination_directe',
  'placement',
  'echauffement',
  'barrage',
  'poules',
  'big_shoot_off',
  'suisse',
  'colline',
]
