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

// Les types que l'atelier signale comme **composables mais pas jouables** (E01US024). Miroir de
// `TYPES_SIGNALES_EN_ECART` côté domaine, dérivé là-bas du registre de contrat de phase
// (`domain/contrat_phase.py`, ADR-0083).
//
// ⚠️ **Écrit en négatif**, à rebours de la table qu'il remplace (`TYPES_DEROULES`, qui vivait dans
// `features/deroule/Deroule.tsx`). Le sens compte : la liste des types *joués* s'allonge à chaque
// US de moteur, donc l'oublier ici faisait **mentir le signal par excès** — l'atelier avertissait
// d'un format que le serveur sait désormais dérouler. La liste des types *en écart*, elle, ne fait
// que **rétrécir** : un oubli y devient un avertissement de trop, jamais un avertissement de moins.
// Entre les deux erreurs possibles, on choisit celle qui ne trompe pas l'organisateur sur ce que
// l'outil sait faire.
//
// L'échauffement n'y figure pas : il ne produit rien **par définition** (« sans point et sans
// classement », §10.1), donc l'annoncer serait un faux positif — et un faux positif répété apprend
// à ignorer le signal.
//
// ⚠️ **Les poules en sont sorties en E05US023**, qui les rend jouables de bout en bout, le **Big
// Shoot Off en E05US028**, et le **système suisse en E05US030** — son moteur était livré par
// E05US026, mais tant qu'aucun écran ne le réglait ni ne le saisissait, le signal restait vrai. Le
// CA l'exige explicitement à chaque fois : le signal doit cesser de viser le format que l'US rend
// jouable **et continuer de viser** les autres, sans quoi il mentirait pour ceux qui restent.
export const TYPES_SIGNALES_EN_ECART: TypePhase[] = ['placement', 'barrage', 'colline']

// Les types que **le moteur** sait dérouler mais que le **bot de simulation** ne sait pas jouer.
//
// ⚠️ **Distinction ajoutée à la revue d'E05US028**, sur un message devenu faux. Côté serveur,
// `_TYPES_DEROULABLES = TYPES_JOUES - {POULES, BIG_SHOOT_OFF}` : la simulation exclut ces deux
// formats, et `LignePhaseSimulee` affichait « le moteur ne sait pas encore dérouler ce type de
// phase ». C'était vrai avant E05US023 et E05US028 ; ce ne l'est plus. Le lot d'origine a retiré le
// signal *honnête* (le bandeau de réserve à la composition) et laissé celui-ci — le seul des deux
// qui trompe, sur l'écran que l'organisateur regarde la veille du tournoi.
//
// La distinction que le serveur documente longuement, le texte affiché ne la faisait pas : ce n'est
// pas le **moteur** qui ne sait pas, c'est le **bot**. Écrit en positif, contrairement à la liste
// ci-dessus, parce qu'il énumère une capacité acquise : un oubli d'ajout ici rend le vieux message
// (« le moteur ne sait pas »), donc pessimiste — jamais un faux « tout va bien ».
export const MOTEUR_SAIT_JOUER: ReadonlySet<TypePhase> = new Set([
  'poules',
  'big_shoot_off',
  'suisse',
])

// Les types sur lesquels une **pause programmée** peut se poser (E05US033, ADR-0091). Miroir de
// `TYPES_ARRETABLES` côté domaine (`domain/contrat_phase.py`), dérivée là-bas de la capacité
// `avancement_lisible` du contrat de phase — et **plus** de `TYPES_DEROULES`, dont elle s'est
// séparée en E05US035 (ADR-0093 : « observer son tour » n'est pas « faire jouer ce type »).
//
// Un arrêt coupe le déroulé à une frontière de tour **observée** : le déclencheur demande le tour
// courant au service qui observe la phase. Les types dont personne ne lit l'avancement —
// l'échauffement, le barrage, le placement, la colline — n'ont aucun tour à observer, et le serveur
// **refuse** l'arrêt (`ArretProgrammeInvalide`, 422). L'écran évite donc de le proposer, et dit
// pourquoi plutôt que de laisser l'organisateur buter sur un refus à la soumission.
//
// ⚠️ **Pour la qualification, le type ne suffit pas** : elle n'est arrêtable qu'une fois
// **découpée en tours**. Non découpée, elle n'en compte qu'un, et toute pause y serait inerte — le
// serveur la refuse à la composition. Cette table reste donc par type, et les deux écrans qui
// composent des phases y ajoutent la condition d'instance (`Phases.tsx`, `Deroule.tsx`).
//
// ⚠️ **Écrite en positif**, comme `MOTEUR_SAIT_JOUER` et pour la même raison : cette liste ne fait
// que **s'allonger**. Un oubli d'ajout prive l'organisateur d'un réglage que le serveur
// accepterait — pessimiste, donc rattrapable ; l'écrire en négatif aurait fait offrir un réglage
// que le serveur refuse, ce qui casse la soumission entière (le `PUT` est une édition **totale**).
//
// ⚠️ **La qualification y entre en `E05US035`, et elle n'y entre pas seule** : elle n'est arrêtable
// que parce que `ServiceSaisie.avancement_de_phase` sait désormais dire où elle en est. Le miroir
// serveur est `TYPES_ARRETABLES` (domaine), qui a cessé d'être `TYPES_DEROULES` à cette occasion —
// la qualification s'**observe** sans être *montée* par personne (ADR-0093). Ajouter un type ici
// sans lecteur d'avancement en face offrirait un réglage inerte, ce que la table sert justement à
// éviter.
export const TYPES_ARRETABLES: ReadonlySet<TypePhase> = new Set([
  'qualification',
  'elimination_directe',
  'poules',
  'big_shoot_off',
  'suisse',
])

// Jusqu'où une phase en tableau départage ses participants (E06US006, ADR-0070).
//
// `un_vers_n` joue **tous** les rangs (placement intégral) ; `top_n` s'arrête au `jusqu_au`-ième,
// les battus des tours antérieurs restant groupés sur leur fourchette. Le catalogue `depth` du
// serveur en compte un troisième (`aucun`) volontairement absent de la façade : c'est le contenu du
// type échauffement, pas un réglage de tableau.
//
// ⚠️ Domicilié ici et non dans une feature (corrigé en revue) : le laisser dans
// `features/patrimoine` faisait importer `shared/ → features/`, la **seule** inversion de ce genre
// du front. `patrimoine/api.ts` et `phases/api.ts` le ré-exportent, donc aucun import existant ne
// casse — le second passe encore par le premier, ce qui reste un saut feature → feature à ranger
// le jour où l'on y touchera.
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
