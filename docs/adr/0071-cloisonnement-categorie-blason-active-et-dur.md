# ADR-0071 — Le cloisonnement catégorie/blason est un réglage de tournoi, dur quand il est actif

- **Statut** : accepté
- **Date** : 04/08/2026
- **US** : E03US007 — Contrainte séparation catégorie/blason
- **Prolonge** : [ADR-0023](0023-moteur-de-placement-glouton-deterministe.md) (glouton déterministe,
  et son seuil d'extraction d'un mécanisme de contraintes),
  [ADR-0024](0024-plan-de-cibles-materialise-ajustable.md) (plan matérialisé, propriétés dérivées),
  [ADR-0047](0047-mixite-clubs-par-reordonnancement-et-signal-derive.md) (mixité de club :
  contrainte **molle** par ré-ordonnancement),
  [ADR-0048](0048-cote-a-cote-des-duellistes-par-reordonnancement.md) (adjacence des duellistes),
  [ADR-0022](0022-hauteur-de-centre-sur-la-categorie.md) (hauteur de centre, contrainte dure)

## Contexte

Le moteur de placement impose depuis E03US001 trois budgets par cible (espace, positions, partage de
carton) et, depuis ADR-0022, une **hauteur unique** par cible. Il trie les archers par
`(hauteur, blason, id)`, ce qui rend les cibles *tendanciellement* homogènes en blason — mais rien
n'interdit à une cible de mêler deux blasons quand il reste de la place : un groupe de triples (1/3)
s'épuise, le blason suivant remplit les deux tiers restants. Et deux **catégories** distinctes qui
tirent le même carton cohabitent sans même être remarquées.

Or le cahier des charges demande l'inverse (EF-4.6, RG-4) :

> **RG-4** — Le cloisonnement par catégorie/blason sur une cible est une **contrainte de placement
> activable**, indépendante du type de tournoi.

Le CA d'E03US007 (« sur une cible, respect du blason associé à la catégorie ; conflits signalés »)
laissait trois questions ouvertes, dont l'une était **explicitement** notée dans la story (« ordre de
priorité des contraintes à confirmer ») : sur quoi cloisonner, avec quelle dureté, et où le réglage
se pose. Elles ont été tranchées au cadrage du 04/08/2026 avec le commanditaire, et reversées dans
`stories/E03-placement.md` (règle 9).

## Décision

### 1. Un réglage à **quatre positions**, porté par le tournoi

`Cloisonnement` — `aucun` (défaut), `categorie`, `blason`, `blason_et_categorie` — est un value
object du domaine (`domain/cloisonnement.py`), stocké sur l'agrégat `Tournoi` (colonne `tournoi.
cloisonnement`, migration `0041`, **NOT NULL** avec défaut `aucun`).

- **Sur le tournoi, pas sur le gabarit** : le gabarit de salle est une brique de patrimoine
  **partagée** entre tournois (E01US023) ; deux tournois montés sur le même plan de salle doivent
  pouvoir cloisonner différemment.
- **Sur le tournoi, pas sur le départ** : la règle est sportive, pas logistique — elle ne change pas
  d'un créneau à l'autre. C'est aussi ce qui permet au **plan de duels** (E03US009) d'obéir au même
  réglage sans réglage supplémentaire : c'est la même salle.
- **`aucun` est une valeur, pas une absence** : la colonne est non nulle. Un `NULL` aurait ouvert un
  cinquième état à traduire dans chaque sens, sans rien signifier de plus.

Le module `domain/cloisonnement.py` **existe séparément du moteur** pour une raison mécanique :
`domain/placement` importe `domain/archer`, qui importe `domain/tournoi`. Loger l'énumération dans le
moteur et l'importer depuis `Tournoi` fermerait un cycle. Le moteur la ré-exporte.

### 2. Contrainte **dure** quand elle est active — et c'est ce qui la distingue de la mixité

La mixité de club (ADR-0047) et le côte à côte des duellistes (ADR-0048) sont des **préférences** :
elles s'obtiennent en ré-ordonnant l'entrée du glouton, ne peuvent jamais échouer, et se signalent
quand elles ne sont pas atteintes. Le cloisonnement est d'une autre nature : **on l'active
délibérément**, et une règle officielle qu'on active pour la voir violée « au mieux » n'a pas de
sens. Il est donc câblé **dans** le glouton (`_CibleEnCours.accueille` / `peut_accueillir`), au même
rang que la hauteur.

Conséquences assumées :

- un archer qu'aucune cible ne peut accueillir **sous** le réglage part en **réserve**, jamais en
  silence (CA « conflits ») ;
- le **déplacement manuel** obéit à la même règle (`cible_accepte`) : une contrainte « dure à la
  génération, molle à la main » se contournerait d'un geste sans que l'admin le sache ;
- l'**ordre de priorité** (question ouverte d'EPIC-03, tranchée ici) devient :
  `capacité / espace / hauteur` (dures, structurelles) > `cloisonnement` (dure, mais **réglable**) >
  `mixité de club` (molle) > `adjacence des duellistes` (molle). Le cloisonnement ne peut que
  **retirer** des cohabitations, jamais en autoriser une — un U11 et un adulte restent séparés quelle
  que soit leur catégorie.
- en plan de **duels**, un tableau ensemencé au scratch peut opposer deux catégories (ADR-0028 :
  `construire_tableau` les ignore). Sous cloisonnement par catégorie, ces duellistes ne peuvent donc
  **pas** être côte à côte : la contrainte dure gagne, et le duel est signalé
  `adjacence_non_garantie` comme n'importe quel duel séparé.

### 3. Les quatre positions, dont deux **aujourd'hui équivalentes** — et pourquoi on les livre quand même

Le blason d'un archer est aujourd'hui celui de sa catégorie (`Categorie.blason_id`). Deux archers de
même catégorie ont donc forcément le même blason : **`blason_et_categorie` rend exactement le même
plan que `categorie`**. La quatrième position est, à ce jour, une redondance.

Elle est livrée quand même, sur choix du commanditaire, parce que la redondance est **datée** : le
cahier des charges prévoit (EF-1.4) qu'une **phase puisse surcharger le blason** (« toutes les
finales sur triples verticaux ») et que l'organisateur choisisse unique vs triple. Le jour où le
blason effectif cessera de dériver de la catégorie, les deux positions divergeront sans qu'aucune
migration ni aucun réapprentissage ne soit nécessaire. Le coût aujourd'hui est d'une valeur
d'énumération et d'un `if` : nettement moins qu'un changement de contrat plus tard.

**Ce que nous ne prétendons pas** : cette position n'apporte rien *aujourd'hui*. Elle est documentée
comme telle dans le code (`domain/cloisonnement.py`), dans la fiche de recette et ici — plutôt que
présentée comme un gain, ce qui aurait faussé la lecture d'un futur relecteur.

### 4. L'indécidable se résout en **refus**, pas en hypothèse favorable

Une `categorie_id` inconnue (`None`) n'est **jamais** réputée identique à une autre : deux archers
sans catégorie connue ne cohabitent pas sous cloisonnement par catégorie. C'est l'esprit d'ADR-0014
(le club inconnu de la mixité), transposé à une contrainte **dure** : là où l'indécidable produisait
un *signal* pour la mixité, il produit ici un *refus*. On ne fait pas l'hypothèse favorable sur une
donnée manquante quand la conséquence est une salle non conforme. En production, le service
renseigne toujours la catégorie ; le cas ne se présente qu'aux frontières.

### 5. Deux propriétés **dérivées**, jamais persistées

- **`cible.cloisonnement_non_respecte`** : la cible mêle ce que le réglage interdit. Le placement
  auto ne peut pas la produire (la contrainte est dure) — elle signale un plan **posé avant**
  l'activation du réglage. Activer le réglage **ne déplace personne** : le plan est matérialisé
  (ADR-0024) et déplacer des archers au changement d'un réglage serait le contraire du serveur
  autoritaire. On **signale**, l'admin régénère ou ajuste. Badge ambre par cible + bannière chiffrée
  qui **dit le geste** (régénérer), sur le modèle exact d'ADR-0047.
- **`RaisonConflit.CLOISONNEMENT`** : l'archer est en réserve *à cause du réglage*, non de la salle.
  Le service la dérive en reposant la question **sans** le cloisonnement : si une cible l'accepterait
  alors, le refus vient du réglage. Le moteur pur, lui, ne rend que `NON_PLACE` — il n'a qu'un monde
  à sa disposition. Deux gestes correctifs différents (desserrer le réglage / ajouter une cible),
  donc deux raisons distinctes, y compris dans le message d'un déplacement refusé.

### 6. **Pas** d'extraction d'un mécanisme de contraintes injectables

ADR-0023 §2 fixait le seuil : « à la 3ᵉ contrainte **et** si une duplication apparaît ». ADR-0047
avait désigné cette US comme « la prochaine occasion de réévaluer ». Verdict : **on n'extrait rien**.

La contrainte ajoute bien un `if` dans le glouton, mais la duplication qu'on redoutait est évitée par
un **prédicat pur unique** — `cible_cloisonnement_non_respecte(cloisonnement, archers)` — dont
`_cloisonnement_admet` est la négation, et que réutilisent tels quels le glouton, la validation d'un
déplacement manuel et le signal calculé à la lecture. Trois chemins, un seul énoncé de la règle.
Introduire un registre de contraintes injectables pour **une** contrainte dure supplémentaire serait
un remède structurel sur une évolution supposée — précisément ce que `CLAUDE.md` interdit (« 3ᵉ
occurrence réelle, invariant déjà dupliqué »). Le seuil reste posé pour la contrainte suivante.

### 7. L'ordre d'entrée groupe par catégorie **quand, et seulement quand, le réglage la sépare**

Le glouton ne revient jamais en arrière (ADR-0023). Si deux catégories partageant un blason
s'entrelacent par `archer_id`, il **ferme une cible à chaque alternance** : le réglage coûterait des
cibles sans rien apporter. La clé de groupe du tri (`_cle_de_groupe`) intègre donc la catégorie —
mais **uniquement** sous un réglage qui la sépare, ce qui garantit que le plan par défaut reste
**identique** à celui d'avant l'US (non-régression stricte, vérifiée par test).

## Conséquences

- **+** RG-4 est tenue : la contrainte s'active, elle ne se subit pas ; par défaut, rien ne change.
- **+** Le cloisonnement vaut partout où l'on place — qualification **et** duels, génération **et**
  glisser-déposer. Aucun écran par lequel le contourner.
- **+** L'organisateur sait **pourquoi** un archer est en réserve et **quoi faire** : le vocabulaire
  distingue « la salle est pleine » de « votre réglage l'exclut ».
- **−** Un cloisonnement strict **consomme des cibles** : chaque catégorie entame sa propre butte et
  l'espace perdu ne se récupère pas (le glouton ne compacte pas). Sur un gabarit juste, il produit de
  la réserve. C'est le prix explicite d'une règle officielle, rendu visible par les conflits — et
  réversible d'un réglage.
- **−** Sur une cible **déjà** non conforme (plan antérieur au réglage), **toute** pose est refusée,
  même « neutre ». Choix de prévisibilité : une règle « ne pas aggraver » dépendrait de l'ordre des
  gestes. L'admin régénère, ou vide la cible d'abord.
- **−** `blason_et_categorie` est aujourd'hui indiscernable de `categorie` (§3) : quatre positions
  pour trois comportements observables tant qu'EF-1.4 n'est pas livré.
- **~** Le réglage reste modifiable **tournoi en cours** : aucun statut ne le verrouille, comme le
  plan lui-même s'ajuste jusqu'au bout (E03US004). Une régénération tardive reste protégée par
  l'alerte d'impact chiffrée (E12US007).
