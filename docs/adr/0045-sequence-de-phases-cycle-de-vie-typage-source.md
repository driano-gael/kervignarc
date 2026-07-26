# ADR-0045 — Séquence de phases : cycle de vie, typage et amorce du modèle de source

- **Statut** : Accepté
- **Date** : 2026-07-26
- **Décideurs** : Organisateur / Architecte
- **Introduit par** : E05US001 (séquence de phases — modèle, édition, cohérence).
- **Raffine** : [ADR-0004](0004-moteur-de-phases-politiques.md) (le moteur manipule une *séquence de
  phases* — cet ADR en pose enfin le modèle **actif**), [ADR-0011](0011-phase-qualification-anticipee.md)
  (la `Phase`, jusqu'ici « minimale et passive », devient une entité d'une **séquence** avec
  cycle de vie et cohérence).
- **S'articule avec** : [ADR-0026](0026-cycle-de-vie-du-tournoi-sept-statuts.md) §3 (le statut
  `en_pause` **de phase** est le second niveau de gel qu'annonçait cet ADR, distinct du `en_pause`
  **de tournoi**).

## Contexte et problème

L'ADR-0004 a décidé que le moteur manipulerait une **séquence de phases** assemblées par politiques
injectables. Mais depuis E01US009/ADR-0011, la `Phase` livrée est **minimale et passive** : un seul
type (`qualification`), un `ordre` et un `statut` conformes au modèle de données mais que **rien
n'exploite** (aucune transition, aucune séquence). Le socle du moteur d'élimination (jalon J2) ne
peut pas se poser tant que ces deux attributs restent inertes.

E05US001 doit rendre la séquence **active** : composer et éditer une suite ordonnée de phases avec
des garde-fous de cohérence, *avant* d'écrire le moteur qui la parcourt (E05US003 politiques,
E05US005 arbre). Trois questions se posent, chacune structurante :

1. **Cycle de vie d'une phase.** Le CA réclame quatre statuts `a_venir / en_cours / en_pause /
   terminee`, dont `en_pause` **gèle la phase** (aucune validation de score acceptée) — que le
   modèle actuel ne connaît pas (il s'arrête à trois, sans `en_pause`).
2. **Typage.** « Typer des phases » n'a de sens que si plusieurs types existent ; or l'enum n'a que
   `qualification`. Combien de types introduire, alors que leur **moteur** (barème de sets, arbre,
   cascade) n'est pas encore écrit ?
3. **Cohérence de peuplement.** Le CA cite « source vide / rangs inexistants / effectif
   incompatible ». Ces contrôles portent sur le **peuplement** d'une phase par une autre (« les 16
   premiers de la qualification »), dont le modèle complet (rangs N→M, gagnants/perdants d'un tour,
   routing en cascade) est le cœur d'**E05US010**, au jalon **J3**. On ne peut pas valider « rangs
   inexistants » contre un modèle de source qui n'existe pas.

## Décision

### 1. Le cycle de vie d'une phase suit le patron du tournoi (ADR-0026 §4)

Quatre statuts : `a_venir → en_cours → terminee`, avec `en_cours ⇄ en_pause` réversible.
**L'agrégat ne porte que la valeur** et des **transitions pures** (`demarrer`, `mettre_en_pause`,
`reprendre`, `terminer`) qui renvoient une copie ; c'est le **service** qui arbitre l'enchaînement
(quel état → quel état) et lève `TransitionStatutInvalide` (→ 409) sur une transition illégale —
exactement comme `ServiceTournois` (règle 2 : la règle vit dans le service/domaine, jamais dans
l'API ; aucune horloge injectée, transitions déclenchées par acte admin, déterministes — règle 9).

`en_pause` **de phase** gèle **une** phase pendant que le reste du tournoi vit ; il coexiste avec le
`en_pause` **de tournoi** (ADR-0026 §3) qui gèle **tout l'événement**. Même mot, même intention
(« figer jusqu'à relance »), deux mailles. **E05US001 pose le statut et ses transitions** ; le
branchement du gel sur le chemin de saisie (refuser une validation quand la phase est `en_pause`)
relève des US de saisie en duels (E04US013) — la qualification n'a qu'une phase, jamais gelée
isolément. Noté pour ne pas laisser croire le gel « actif » partout dès maintenant.

### 2. Typage ouvert, sans préjuger du moteur

`TypePhase` gagne `elimination_directe` et `placement`, aux côtés de `qualification`. Ce sont les
types dont la **règle est écrite** (catalogue de `stories/E05-moteur-phases.md`) et qui composent
les séquences proches (qualif → élim directe, qualif → placement). **Déclarer** une phase d'un type
ne présuppose pas que son **moteur** existe : E05US001 modélise la séquence, pas son exécution. Les
autres types (barrage, finale, Big Shoot Off, poules…) s'ajouteront à l'enum **quand leur US les
implémentera** — pas avant, pour ne pas offrir en façade un type qu'aucun moteur ne sait dérouler.

Conséquence sur l'agrégat : `bareme` et `validation` (les deux politiques de qualification) deviennent
**facultatifs** — une phase `elimination_directe` n'a pas de barème de qualification. Ils restent
**obligatoires pour une phase `qualification`** (invariant vérifié à la construction) ; leurs
politiques propres (scoring de sets, seeding…) viendront dans la `config` via E05US003. **On ne
touche pas** à la forme de `config` : elle reste **à plat** (`config.scoring`, `config.validation`),
la bascule vers `config.policies` est explicitement assignée à E05US003 (**DETTE-003**), pas ici.

### 3. Amorce d'un modèle de source **minimal**, assumé provisoire

Une phase peut déclarer **une** source : « alimentée par les rangs [début..fin] de la phase d'ordre
*k* », modélisée par un value object `SourcePhase(ordre_source, rang_debut, rang_fin)` et un
`effectif` facultatif sur chaque phase (nombre de participants qu'elle classe/produit). Cela suffit
à rendre les trois contrôles du CA **décidables et testables** :

| Contrôle (CA) | Règle vérifiée | Où |
|---|---|---|
| **source vide** | `rang_debut ≤ rang_fin` (plage non vide) et `rang_debut ≥ 1` | invariant du VO `SourcePhase` (domaine) |
| **rangs inexistants** | si la phase source déclare un `effectif` E : `rang_fin ≤ E` | `SequencePhases` (domaine) |
| **effectif incompatible** | si la phase consommatrice déclare un `effectif` F : `rang_fin − rang_debut + 1 = F` | `SequencePhases` (domaine) |
| (structure) | `ordre_source` désigne une phase **existante** et **antérieure** ; ordres contigus 1..N | `SequencePhases` (domaine) |

La cohérence vit dans un **agrégat de séquence** `SequencePhases` (frozen, valide à la construction) :
la règle est **pure et testable depuis le CA** (règle 2/9), le service assemble les phases relues du
dépôt en `SequencePhases` — dont la construction rejette une séquence incohérente — avant de
persister. Les erreurs de cohérence sont des `DomainError` (→ 422 : une édition incohérente est une
**entrée invalide**, pas un conflit d'état).

**Ce modèle est une amorce, pas le modèle cible.** E05US010 (J3) le remplacera par le peuplement
complet : sources multiples (gagnants **et** perdants d'un tour), routing en cascade, division
récursive des plages. La source unique « par rangs » d'aujourd'hui en est le sous-ensemble le plus
simple. Ce choix — anticiper une part d'E05US010 plutôt que reporter tout contrôle de source — a été
**arbitré avec le commanditaire** (26/07/2026) en connaissance du risque : figer un modèle qu'E05US010
retravaillera. Il est **borné** (une source, un intervalle de rangs, pas de routing) précisément pour
que ce retravail reste peu coûteux. Inscrit à ce titre en **dette de conception assumée** (voir
`docs/dette.md`, DETTE-015).

## Conséquences

- **+** La séquence de phases devient **active** : le jalon J2 a son socle (E05US003 assemble les
  politiques sur ces phases, E05US005 construit l'arbre à partir de la séquence).
- **+** Le cycle de vie de phase réutilise **tel quel** le patron du tournoi (agrégat = valeur,
  service = enchaînement) : aucune mécanique nouvelle à inventer ni à tester à part.
- **+** Les trois contrôles de cohérence du CA sont **décidables** dès maintenant, sans attendre le
  moteur de peuplement complet.
- **−** Un **modèle de source provisoire** (DETTE-011) qu'E05US010 devra élargir/retravailler —
  assumé et borné pour en limiter le coût.
- **−** `TypePhase` s'ouvre à des types **sans moteur** : on peut déclarer une phase
  `elimination_directe` qu'aucun code ne sait encore dérouler. C'est voulu (modéliser la séquence
  avant de l'exécuter), mais l'UI doit le **dire** (un type non exécutable est un jalon de
  préparation, pas une promesse de déroulé).
- **−** `bareme`/`validation` facultatifs sur `Phase` : le code qui les lisait doit gérer `None`
  hors qualification (l'invariant « qualification ⇒ barème+grain » ferme le seul cas dangereux).

## Liens
`stories/E05-moteur-phases.md` (E05US001), ADR-0004, ADR-0011, ADR-0026 §3, `docs/dette.md`
(DETTE-003 assignée à E05US003 ; DETTE-015 modèle de source provisoire), `moteur-placement-lucky-loser.md`.
