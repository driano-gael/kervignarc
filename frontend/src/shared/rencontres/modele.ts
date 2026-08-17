// Le modèle **neutre** des formats sans arbre (E05US031, ADR-0089 §1) — logique pure, testée en
// node, aucune dépendance à React.
//
// **Pourquoi ce module existe.** Trois formats jouables n'ont pas d'arbre : les poules, le système
// suisse et le Big Shoot Off. Les deux premiers partagent le décor `RONDES_APPARIEES` du contrat de
// phase (ADR-0083 §1) et donc la même grammaire de lecture — *des rencontres appariées, groupées par
// tour ou par ronde, et un classement qui dit où en est chacun*. Ils sont rendus par **un seul**
// composant, alimenté par les types d'ici ; le Big Shoot Off garde sa vue propre (sa manche est un
// tir collectif sans adversaire, l'y plier demanderait d'inventer des champs vides).
//
// ⚠️ **Le critère d'entrée est le décor, pas le compte de formats** (ADR-0089 §1). La colline
// (`E05US027`) apparie elle aussi : elle entrera ici sans qu'on écrive une vue. Un format qui
// n'apparie pas aura la sienne.
//
// ⚠️ **L'adaptation vit dans la feature du format, le rendu vit ici.** Ce module ne connaît ni
// `EtatPoules` ni `EtatSuissePublique` : les faire entrer ferait importer `shared/ → features/`, la
// seule inversion que le front n'ait jamais tolérée (cf. l'en-tête de `shared/phases/catalogue.ts`,
// corrigé en revue pour cette raison exacte). Chaque feature écrit son `publique.ts`.
//
// ⚠️ **La logique naît hors du JSX, et c'est délibéré.** ADR-0064 §2 en tire l'enseignement le plus
// cher du projet : *une garantie annoncée dans un ADR n'existe que si un chemin de code la produit —
// et qu'un test l'exerce*. « Mon chemin » de l'arbre a dû être extrait du JSX **après** livraison ;
// celui-ci est dehors dès le premier jour.

import type { Place } from '../salle/place'

/** Le camp d'un duelliste dans une rencontre. Miroir de `domain.duel.Cote`. */
export type Cote = 'haut' | 'bas'

/** Où en est l'archer sur une étape de son chemin.
 *
 * ⚠️ **Domicilié ici depuis E05US031, et non plus dans `features/tableaux/presentation.ts`** :
 * quatre surfaces le lisent désormais (l'arbre, le récapitulatif de journée, les poules, le suisse).
 * `presentation.ts` le **ré-exporte**, donc aucun import existant ne casse — c'est le geste
 * qu'`E05US030` a fait pour `Place`, et pour le même motif : un vocabulaire dupliqué finit par
 * diverger (`DETTE-020` en compte déjà deux sur cette seule feature).
 *
 * `en_attente` est le statut sans lequel la vue ment : la rencontre est allée au bout, le scoreur
 * n'a pas encore scellé. `a_venir` est une étape **sans rencontre** — un tour que le format porte
 * encore et que l'archer atteindra.
 */
export type StatutEtape =
  'gagne' | 'perdu' | 'en_attente' | 'a_jouer' | 'attente_adversaire' | 'exempt' | 'a_venir'

/** Ce qu'on écrit en face de chaque étape. **Un mot par situation, jamais une couleur seule**
 * (`DV-03`) : l'écran de salle est vu de loin et l'appli publique est lue en plein soleil. */
export const LIBELLE_STATUT: Record<StatutEtape, string> = {
  gagne: 'Gagné',
  perdu: 'Perdu',
  en_attente: 'En attente de validation',
  a_jouer: 'À tirer',
  attente_adversaire: 'Adversaire à désigner',
  exempt: 'Exempt',
  a_venir: 'À venir',
}

/** Un archer tel qu'une vue publique le nomme. `archer_id` sert à reconnaître un **archer suivi**
 * sans comparer des noms — comparaison qui casse au premier homonyme, et il y en a. */
export interface ArcherPublic {
  archer_id: number
  nom: string
  prenom: string
}

/** Une rencontre **en consultation** : l'avancement, jamais le détail de saisie.
 *
 * `termine` et `validee` ne disent pas la même chose et l'écart est **visible à l'écran** : le tir
 * est allé au bout, le scoreur n'a pas encore scellé.
 */
export interface RencontreVue {
  numero: number
  haut: ArcherPublic | null
  bas: ArcherPublic | null
  /** Les deux places de tir, ou `null` si le plan de la phase n'est pas posé. */
  couloirs: [Place, Place] | null
  points_haut: number | null
  points_bas: number | null
  vainqueur: Cote | null
  termine: boolean
  validee: boolean
  /** Un tir existe en base mais oppose d'autres duellistes — la population a bougé sous un score
   * déjà saisi. Le serveur le masque et refuse de l'écraser : la rencontre est **bloquée**, pas
   * « à tirer ». Le public n'a pas à comprendre pourquoi, mais il ne doit pas lire un score faux. */
  bloquee: boolean
}

/** Un groupe de rencontres jouées ensemble — un **tour** de poule, une **ronde** de suisse.
 *
 * `libelle` est rédigé par l'adaptateur du format (« Ronde 3 », « Tour 2 ») : c'est du vocabulaire
 * métier, et il n'a qu'un domicile par format (règle 3).
 */
export interface TourVue {
  libelle: string
  rencontres: RencontreVue[]
  /** L'archer **exempt** de ce tour, s'il y en a un — le porteur du bye en système suisse.
   *
   * ⚠️ Porté ici et **non** comme une rencontre sans adversaire (choix d'E05US031) : une rencontre
   * fantôme apparaîtrait dans la liste sous la forme « X vs — », qui se lit comme un appariement en
   * attente alors que personne ne viendra. Le bye est une propriété du tour, pas une opposition.
   */
  exempt: ArcherPublic | null
  /** Le tour est-il **clos** — toutes ses rencontres validées ? En système suisse c'est ce qui
   * conditionne l'ouverture du suivant, et l'écran doit pouvoir le dire au lieu de laisser croire à
   * une panne. */
  clos: boolean
}

/** Une colonne de classement, propre au format : « Pts », « Buchholz », « Δ sets »… */
export interface ColonneClassement {
  cle: string
  libelle: string
  /** L'explication en toutes lettres, rendue en `title` : la moitié de ces critères est inconnue de
   * qui regarde. « Buchholz » n'apprend rien sans « somme des points des adversaires rencontrés ». */
  aide: string
}

/** Une ligne de classement. `valeurs` est **alignée sur `colonnes`**, déjà rédigée par l'adaptateur
 * du format — c'est lui qui sait qu'un point de suisse se stocke en demi-points doublés. */
export interface LigneClassement {
  rang: number
  archer_id: number
  nom: string
  valeurs: string[]
  ex_aequo: boolean
}

/** Un bloc de rencontres autonome : **une poule**, ou l'unique plateau d'un système suisse. */
export interface BlocRencontres {
  cle: string
  /** Le nom du bloc (« Poule 3 »), ou `null` quand le format n'en a qu'un — un titre « Plateau 1 »
   * au-dessus du seul plateau n'apprend rien et coûte une ligne sur 360 px. */
  titre: string | null
  tours: TourVue[]
  colonnes: ColonneClassement[]
  classement: LigneClassement[]
  /** Ce que la vue doit **dire** : un barrage requis, un plan de salle non posé. Rapporté, jamais tu
   * (ADR-0024). */
  notes: string[]
}

/** Une phase sans arbre, prête à rendre. */
export interface FormatPublic {
  blocs: BlocRencontres[]
  /** Ce que la phase n'a pas pu produire, et pourquoi — les conflits de pose de plan. */
  conflits: string[]
}

export function nomComplet(qui: ArcherPublic): string {
  return `${qui.prenom} ${qui.nom}`.trim()
}

/** Le camp occupé par un archer dans une rencontre, ou `null` s'il n'y figure pas. */
export function coteDe(rencontre: RencontreVue, archerId: number): Cote | null {
  if (rencontre.haut?.archer_id === archerId) return 'haut'
  if (rencontre.bas?.archer_id === archerId) return 'bas'
  return null
}

/** Le score **du point de vue d'un camp** — l'archer suivi est toujours à gauche. */
export function scoreVu(rencontre: RencontreVue, cote: Cote): string | null {
  const { points_haut: haut, points_bas: bas } = rencontre
  if (haut === null || bas === null) return null
  return cote === 'haut' ? `${haut} — ${bas}` : `${bas} — ${haut}`
}

/** Où en est l'archer sur cette rencontre.
 *
 * ⚠️ **`validee`, pas `termine`.** Tant que le scoreur n'a pas scellé, le résultat n'est pas acquis :
 * annoncer « gagné » promettrait un rang que la ligne suivante dément. C'est le piège n°1 de
 * `features/tableaux/presentation.ts`, et il vaut ici mot pour mot.
 *
 * Une rencontre **bloquée** (désynchronisée) est rendue « à tirer » et non « à valider » : le
 * serveur masque son tir et refuse de l'écraser, donc rien n'est acquis de ce côté-là non plus.
 */
export function statutDe(rencontre: RencontreVue, cote: Cote): StatutEtape {
  if (rencontre.bloquee) return 'a_jouer'
  if (rencontre.validee && rencontre.vainqueur !== null) {
    return rencontre.vainqueur === cote ? 'gagne' : 'perdu'
  }
  if (rencontre.termine) return 'en_attente'
  const adversaire = cote === 'haut' ? rencontre.bas : rencontre.haut
  return adversaire === null ? 'attente_adversaire' : 'a_jouer'
}

/** Une étape du chemin d'un archer suivi. */
export interface EtapeChemin {
  /** Le tour qui la porte (« Ronde 3 »), tel que l'adaptateur du format l'a rédigé. */
  libelle: string
  /** Le bloc, quand le format en a plusieurs (« Poule 3 ») — `null` sinon. */
  bloc: string | null
  adversaire: ArcherPublic | null
  statut: StatutEtape
  /** Le score **vu de l'archer suivi** (« 6 — 2 »), ou `null` si rien n'est tiré. */
  score: string | null
}

/** Le chemin d'un archer dans une phase : ses rencontres, tour par tour, dans l'ordre.
 *
 * ⚠️ **Aucune étape « à venir » n'est fabriquée ici**, à la différence de l'arbre. La raison est
 * structurelle et non un manque : dans un tableau, le nombre de tours est connu d'avance et la
 * branche dit ce qui reste à jouer ; dans un système suisse, la ronde N+1 **n'existe pas** tant que
 * la N n'est pas close, et l'appariement en dépend. Promettre une ligne « Ronde 4 · À venir »
 * affirmerait à la fois qu'elle aura lieu et qu'il n'y a personne en face — deux paris, dont un
 * faux dès que la phase s'arrête à trois rondes.
 *
 * Le bye **est** une étape : l'archer exempt d'une ronde n'a pas tiré, et l'omettre laisserait un
 * trou inexpliqué dans un chemin par ailleurs continu.
 */
export function cheminDe(format: FormatPublic, archerId: number): EtapeChemin[] {
  const etapes: EtapeChemin[] = []
  for (const bloc of format.blocs) {
    for (const tour of bloc.tours) {
      if (tour.exempt?.archer_id === archerId) {
        etapes.push({
          libelle: tour.libelle,
          bloc: bloc.titre,
          adversaire: null,
          statut: 'exempt',
          score: null,
        })
        continue
      }
      for (const rencontre of tour.rencontres) {
        const cote = coteDe(rencontre, archerId)
        if (cote === null) continue
        etapes.push({
          libelle: tour.libelle,
          bloc: bloc.titre,
          adversaire: cote === 'haut' ? rencontre.bas : rencontre.haut,
          statut: statutDe(rencontre, cote),
          score: scoreVu(rencontre, cote),
        })
      }
    }
  }
  return etapes
}

/** La ligne de classement d'un archer, et le bloc qui la porte — `null` s'il n'est pas classé.
 *
 * Utile pour « mon chemin » : dans un format sans arbre, le rang **est** la position. Sans lui, la
 * vue centrée sur un archer suivi dirait ce qu'il a joué sans jamais dire où il en est.
 */
export function rangDe(
  format: FormatPublic,
  archerId: number,
): { bloc: BlocRencontres; ligne: LigneClassement } | null {
  for (const bloc of format.blocs) {
    const ligne = bloc.classement.find((l) => l.archer_id === archerId)
    if (ligne !== undefined) return { bloc, ligne }
  }
  return null
}

/** Le nom d'un archer, **lu dans la phase** — jamais mémorisé côté client.
 *
 * Un archer renommé garde ainsi son suivi sans afficher un nom périmé (`sessionSuivisStore` ne
 * stocke que des identifiants). Deux sources, dans cet ordre : le classement, qui nomme tout le
 * monde, puis les appariements, pour le cas d'un archer inscrit avant que le classement n'existe.
 */
export function nomDeArcher(format: FormatPublic, archerId: number): string | null {
  const classe = rangDe(format, archerId)
  if (classe !== null) return classe.ligne.nom
  for (const bloc of format.blocs) {
    for (const tour of bloc.tours) {
      if (tour.exempt?.archer_id === archerId) return nomComplet(tour.exempt)
      for (const rencontre of tour.rencontres) {
        const cote = coteDe(rencontre, archerId)
        if (cote === 'haut' && rencontre.haut !== null) return nomComplet(rencontre.haut)
        if (cote === 'bas' && rencontre.bas !== null) return nomComplet(rencontre.bas)
      }
    }
  }
  return null
}

/** Un conflit de placement, **rédigé pour un spectateur**.
 *
 * ⚠️ **`ConflitReponse.raison` est un code, pas une phrase.** Le serveur y sert la valeur de l'enum
 * `RaisonConflitBloc` — `non_posee`, `salle_pleine`, `sans_rencontre`. Les deux adaptateurs
 * publics le recopiaient tel quel, si bien que l'écran du gymnase affichait littéralement
 * « **non_posee** » — et pour le système suisse c'était le régime **nominal**, le serveur renvoyant
 * `_PLAN_A_REPOSER` tant que le plan n'est pas posé. Relevé par l'axe adversarial.
 *
 * ⚠️ **Registre public, distinct de celui de l'organisateur.** `decrireConflits`
 * (`features/phases/Phases.tsx`) dit à l'organisateur *quoi faire* (« la salle est trop petite »,
 * qui appelle une action) ; ici on dit au spectateur *ce qu'il voit* — pourquoi les cibles
 * manquent, sans lui demander d'agir. Même enum, deux publics.
 *
 * `groupe` nomme le bloc quand il y en a plusieurs (« Poule 3 ») ; `null` pour le plateau unique du
 * suisse, où préfixer n'apprendrait rien. */
export function libelleConflit(raison: string, groupe: string | null = null): string {
  const prefixe = groupe === null ? '' : `${groupe} — `
  const libelles: Record<string, string | undefined> = {
    non_posee: 'le plan de tir n’est pas encore posé : les cibles s’afficheront dès qu’il le sera.',
    salle_pleine: 'pas assez de couloirs libres dans la salle : les cibles ne sont pas attribuées.',
    sans_rencontre: 'aucune rencontre à tirer.',
  }
  const phrase = libelles[raison] ?? 'les cibles ne sont pas encore attribuées.'
  return `${prefixe}${phrase.charAt(0).toUpperCase()}${phrase.slice(1)}`
}

/** Les archers de `suivis` qui figurent réellement dans cette phase, dans l'ordre donné.
 *
 * ⚠️ **« Aucun de vos archers ici » n'est pas « rien à afficher »** (ADR-0089 §6). Le cas est banal
 * — on suit des archers d'une catégorie, on regarde la poule d'une autre — et c'est ce qu'E16US004
 * a dû corriger en revue sur l'arbre, faute d'avoir su distinguer les deux vides.
 */
export function engagesParmi(format: FormatPublic, suivis: number[]): number[] {
  return suivis.filter(
    (archerId) => cheminDe(format, archerId).length > 0 || rangDe(format, archerId) !== null,
  )
}
