// Le **catalogue des types de phase**, côté front : l'union, ses libellés, ses aides (ADR-0062).
//
// ⚠️ **Domicile unique** : `features/phases/api.ts` et `features/patrimoine/api.ts` ré-exportent
// d'ici, seul point à synchroniser avec l'enum `TypePhase` du backend. ⚠️ **Exhaustivité
// obligatoire** : chaque table est un `Record<TypePhase, …>`, jamais un ternaire à repli — c'est un
// repli qui a fait afficher six types comme « Placement » sans que TypeScript bronche.

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
// ⚠️ **Dérogation explicite au ⚠️ d'en-tête** : celui-ci interdit les replis **dans les tables** ;
// ici le repli ne s'arme que pour une chaîne **hors union**, donc un serveur plus récent que ce
// bundle (déploiement décalé). ⚠️ Le cast porte sur la **table**, pas sur la valeur :
// `LIBELLE_TYPE[type as TypePhase] ?? type` rendait le `??` mort pour le compilateur alors qu'il
// est le seul filet réel. Domicile ici : deux features en avaient écrit une copie chacune.
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
// `TYPES_SIGNALES_EN_ECART` côté domaine (ADR-0083).
//
// ⚠️ **Écrit en négatif**, à rebours de la table qu'il remplace : la liste des types *joués*
// s'allonge à chaque US de moteur, donc un oubli y ferait **mentir le signal par excès** ; celle
// des types *en écart* ne fait que rétrécir — un oubli y devient un avertissement de trop. ⚠️ Les
// deux qui restent n'attendent aucune US : le `placement` n'a aucun service pour monter son arbre
// (ADR-0083), et le `barrage` est un **départage**. Cette liste ne se videra donc pas.
export const TYPES_SIGNALES_EN_ECART: TypePhase[] = ['placement', 'barrage']

// Les types que **le moteur** sait dérouler mais que le **bot de simulation** ne sait pas jouer.
//
// ⚠️ **Distinction ajoutée à la revue d'E05US028, sur un message devenu faux** :
// `LignePhaseSimulee` affichait « le moteur ne sait pas encore dérouler ce type », vrai avant
// E05US023/E05US028 et faux depuis. Ce n'est pas le **moteur** qui ne sait pas, c'est le **bot**.
// Écrit en positif — il énumère une capacité acquise, donc un oubli rend le vieux message,
// pessimiste et jamais faussement rassurant.
export const MOTEUR_SAIT_JOUER: ReadonlySet<TypePhase> = new Set([
  'poules',
  'big_shoot_off',
  'suisse',
  // ⚠️ **Oubliée à la livraison d'E05US027, relevée par l'axe adversarial.** Le backend avait bien
  // retiré la colline de `_TYPES_DEROULABLES` (le bot ne sait pas la simuler), mais ce miroir-ci
  // n'avait pas suivi : l'atelier affichait donc « le moteur ne sait pas encore dérouler ce type de
  // phase » sur le format que l'US venait précisément de rendre jouable. Exactement le défaut
  // corrigé en revue d'E05US028, rejoué un format plus loin — et le seul des deux signaux qui
  // trompe. Le garde-fou est désormais `features/deroule/MessageDuBot.test.tsx`, pas ce
  // commentaire — et il garde les **quatre types d'aujourd'hui**, pas un cinquième à venir.
  'colline',
])

// Les types dont les archers sont placés **par bloc de couloirs**, donc qui offrent un geste de
// pose de plan. Miroir de `ContratDePhase.plan_de_cibles` côté domaine.
//
// ⚠️ **Cette table existe pour rendre un garde-fou VRAI, pas pour factoriser trois lignes.** Le
// même défaut s'est produit trois fois (E05US023, E05US030, E05US027) : le hook et la route
// existaient, l'appelant manquait, et personne ne savait sur quelle cible tirer. En dérivant le
// montage **et** le test de cette table, la récidive se déplace vers la table — progrès réel, pas
// garantie totale : rien ne compare mécaniquement les deux tables.
export const TYPES_A_PLAN_PAR_BLOCS: ReadonlySet<TypePhase> = new Set([
  'poules',
  'suisse',
  'colline',
])

// Les types sur lesquels une **pause programmée** peut se poser (E05US033, ADR-0091). Miroir de
// `TYPES_ARRETABLES` côté domaine, dérivée de `avancement_lisible` — et **plus** de
// `TYPES_DEROULES`, dont elle s'est séparée en E05US035 (ADR-0093).
//
// ⚠️ **Pour la qualification, le type ne suffit pas** : elle n'est arrêtable qu'une fois **découpée
// en tours**, condition d'instance ajoutée par `Phases.tsx` et `Deroule.tsx`. ⚠️ **Écrite en
// positif** : un oubli prive d'un réglage que le serveur accepterait (pessimiste, rattrapable), là
// où le négatif ferait offrir un réglage refusé — et le `PUT` étant total, tout échouerait.
export const TYPES_ARRETABLES: ReadonlySet<TypePhase> = new Set([
  'qualification',
  'elimination_directe',
  'poules',
  'big_shoot_off',
  'suisse',
  // E05US027 : la colline y entre parce que `ServiceColline.avancement_de_phase` sait désormais
  // dire où elle en est — pas parce qu'elle est « jouable ». C'est la distinction qu'ADR-0093 a
  // posée et que le miroir serveur (`TYPES_ARRETABLES`, dérivée d'`avancement_lisible`) applique.
  'colline',
])

// Jusqu'où une phase en tableau départage ses participants (E06US006, ADR-0070).
//
// `un_vers_n` joue **tous** les rangs ; `top_n` s'arrête au `jusqu_au`-ième, les battus antérieurs
// restant groupés. Le catalogue serveur en compte un troisième (`aucun`) volontairement absent de
// la façade : c'est le contenu du type échauffement, pas un réglage de tableau. ⚠️ Domicilié ici et
// non dans une feature : le laisser dans `features/patrimoine` faisait importer `shared/ →
// features/`, la **seule** inversion de ce genre du front.
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
