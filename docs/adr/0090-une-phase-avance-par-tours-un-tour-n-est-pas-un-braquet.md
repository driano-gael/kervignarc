# ADR-0090 — Une phase avance par tours ; un tour n'est pas un braquet

- **Statut** : Accepté
- **Date** : 2026-08-18
- **US** : E05US032 (prépare E05US033)
- **Complète** : [ADR-0083](0083-le-contrat-de-phase-jouable.md) (le contrat de phase jouable)
- **Voisin** : [ADR-0084](0084-un-seul-port-de-lecture-de-classement-resolu-par-type.md) — dont cet
  ADR reprend le patron de port, à la lettre

## Contexte

Le projet emploie **quatre mots** pour désigner la progression d'une phase, et chacun est le bon mot
du métier à sa place :

| Format | Le mot de la salle | Ce que porte le code |
|---|---|---|
| Élimination directe, placement | *tour* (« quart de finale ») | `Match.tour`, `TourBraquet.tour` |
| Poules | *tour* | les tours du round-robin, dans `ServicePoules` |
| Système suisse, colline | *ronde* | `RondeAffichee`, `domain/suisse.py` |
| Big Shoot Off | *manche* | les manches, `domain/big_shoot_off.py` |
| Qualification, échauffement | *volée*, *série* | `BaremeQualification.nb_volees` |

La pluralité **à l'écran** est voulue et protégée par la règle 3 : un archer qui tire une demi-finale
n'entend pas « ronde 3 » au micro, et le glossaire assume déjà une homonymie du même ordre (« manche »
d'un duel vs « manche » d'un Big Shoot Off, *« levée par le contexte de phase »*).

Mais **dans le code, il n'existe aucun concept commun** — et l'absence a une conséquence mesurable.
`domain/suivi_deroule.py` construit son `AvancementTour` **sur les braquets** (`TourBraquet`), c'est-
à-dire sur les tranches de rangs d'un tableau. Le commentaire du module le dit sans le nommer :

> Une phase sans braquet (qualification, ou type dont le moteur ne déduit pas les tours,
> `# DETTE-028`) rend un bloc à **zéro tour**.

Autrement dit : le suivi du déroulé sait dire « on attaque les quarts » d'un tableau, et **ne sait
rien dire** d'une qualification, d'une poule, d'un système suisse ou d'un Big Shoot Off en cours. Cinq
implémentations privées, aucune abstraction — le seuil du § *Dette* de `CLAUDE.md` pour un remède
structurel (3ᵉ occurrence réelle dans le code d'aujourd'hui) est largement franchi, et la preuve n'est
pas une évolution supposée : elle est dans le module ci-dessus.

Le déclencheur immédiat est `E05US033` (programmer les pauses d'un déroulé), qui a besoin de désigner
*« après quel tour »* une phase s'arrête, quel que soit son format. Mais la décision ne lui est pas
subordonnée : le trou du suivi existe indépendamment.

## Décision

### 1. Le **tour** est l'unité d'avancement générique d'une phase

Toute phase, quel que soit son type, compte **N tours numérotés de 1 à N**, et sait dire lequel est en
cours. Aucun type n'en est exclu — la qualification et l'échauffement en comptent **un**, ce qui est
vrai (la phase entière est un tour) et non un cas dégénéré à traiter à part.

### 2. Un tour est une unité d'**avancement**, jamais de **classement**

C'est l'invariant central, et c'est celui que le code viole aujourd'hui.

- Certaines phases **classent au fil des tours** : chaque tour d'une élimination directe attribue une
  tranche de rangs — le **braquet**, la *Règle R* de `moteur-placement-lucky-loser.md`.
- D'autres **ne classent qu'à la fin** : une qualification produit un total, pas un classement à la
  volée 12.

Le braquet est donc une propriété que **certains** tours ont, jamais la définition d'un tour.
`TourBraquet` reste ce qu'il est et ne change pas de sens ; ce qui change, c'est que le tour cesse
d'en être **dérivé**.

### 3. Le nombre de tours est **dérivé** quand la structure le détermine, **1** sinon

| Type | Nombre de tours | Origine |
|---|---|---|
| Élimination directe, placement | nombre de braquets | structure du tableau |
| Poules | tours du round-robin | taille de poule |
| Système suisse, colline | nombre de rondes réglé | `ConfigurationSuisse.nb_rondes`, borné par l'effectif |
| Big Shoot Off | nombre de manches | `paliers` |
| Qualification, échauffement | **1** | rien ne le détermine |

Pour les deux derniers, « en combien de tours découper 20 volées » est un **choix de l'organisateur**,
pas une propriété de la structure. Ce réglage est délibérément **hors de cet ADR** : il est porté par
`E05US033`, là où il sert. Poser ici un champ que rien ne lit coûterait une migration pour rien.

### 4. Le **libellé** est le mot du métier, résolu par le type de phase

Un numéro de tour ne s'affiche jamais nu. Le contrat de phase ([ADR-0083](0083-le-contrat-de-phase-jouable.md))
— l'endroit où chaque format répond aux questions « comment on me joue » — gagne la question **« en
combien de tours, et sous quel nom ? »**.

```
tour 3 d'un tableau de 16   →  « Demi-finale »      (distance à la finale, jamais le rang)
tour 3 d'une poule          →  « Tour 3 »
tour 3 d'un système suisse  →  « Ronde 3 »
tour 3 d'un Big Shoot Off   →  « Manche 3 »
l'unique tour d'une qualif  →  (aucun libellé — il n'y a rien à distinguer)
```

⚠️ **La résolution générique absorbe l'existante, elle ne s'y ajoute pas.** Le libellé de tour d'un
tableau a déjà **deux domiciles** (`DETTE-020` : `domain/tableau.py` et le front
`saisie-duels/duel.ts`), et `E07US005` a failli en ouvrir un troisième avant de le refermer en
*servant* le libellé du domaine au DTO. Le point d'entrée générique **délègue** à la fonction du
tableau ; il n'en réimplémente pas la logique — la petite finale se nomme par sa plage et non par sa
distance au titre, et ce genre de règle ne se recopie pas.

### 5. « Où en est cette phase ? » est un **port étroit résolu par type**

Le nombre de tours d'un **tableau** se lit dans la projection, qui le calcule déjà à l'atelier. Pour
les autres formats, ni le nombre ni le tour courant ne se déduisent sans données : un système suisse
réglé à 7 rondes n'en joue que 5 si l'effectif ne permet pas plus, et « quelle ronde tourne » dépend
de ce qui est validé. Les **deux** nombres viennent donc du service qui déroule la phase.

Plutôt qu'un second mécanisme, cet ADR **reprend à la lettre** le patron d'[ADR-0084](0084-un-seul-port-de-lecture-de-classement-resolu-par-type.md) :
un port étroit, réalisé par les services de format, **branché par type au composition root**
(règle 8), et consommé par le seul service qui pose la question. Le suivi ne connaît aucun service de
format : il connaît **cette question**, et `bootstrap/` dit qui y répond.

Une phase dont aucun lecteur n'est branché rend son **nombre** de tours (structurel) sans tour
courant — dégradation lisible, pas exception. L'écran de salle tourne en permanence, souvent sans
personne devant : une phase muette y coûte une ligne incomplète, une exception y coûte la journée.

## Conséquences

- **Le suivi du déroulé cesse d'être aveugle hors tableau.** Une qualification, une poule, un système
  suisse et un Big Shoot Off en cours affichent enfin où ils en sont. C'est la surface visible de
  l'US, et elle **rétrécit** le volet « le suivi ne sait pas dessiner les tours » de `DETTE-028` —
  sans la refermer : le cœur de cette dette (des moteurs sans consommateur de production) n'est pas
  ce qui se joue ici.
- **`E05US033` devient écrivable.** « S'arrêter après le tour 3 » a un sens sur les six formats, avec
  un seul champ et un seul vocabulaire, au lieu de cinq pilotages jumeaux à écrire puis à fondre.
- **Un type de phase neuf devra répondre à une question de plus** au contrat : en combien de tours,
  sous quel nom. C'est le coût assumé — et c'est le même que celui d'ADR-0083, qui a déjà fait ce
  choix pour six autres questions.
- **Le branchement est tardif et visible**, comme pour ADR-0084 : un service de format est construit
  puis enregistré auprès du suivi. Un cycle qu'on ne voit pas est un cycle qu'on réintroduit — donc
  il est explicite dans `bootstrap/`, jamais derrière un import paresseux.
- **Risque assumé** : le libellé générique devient un point de passage obligé. S'il se met à
  réimplémenter ce que `domain/tableau.py` sait déjà faire, `DETTE-020` gagne un troisième domicile
  au lieu d'en perdre un. La revue doit le vérifier explicitement.

## Porté dans le code par

- `backend/domain/contrat_phase.py` — `UniteDeTour` et `ContratDePhase.unite_de_tour` : la 7ᵉ
  question du contrat. L'unité vit **avec** les six autres, faute de quoi le contrat importerait le
  module qui l'importe.
- `backend/domain/tour_de_phase.py` — `unite_de_tour`, `libelle_de_tour` : la résolution en mot de la
  salle, qui **délègue** à `domain.tableau.libelle_tour` pour l'arbre.
  ⚠️ **Ce module ne calcule pas le nombre de tours**, contrairement à ce que la première rédaction de
  cet ADR annonçait (une classe `ToursDePhase` y était nommée avant d'être écrite — exactement le
  défaut que `CLAUDE.md` met en garde : *« nommer un module vide reproduit le défaut d'ADR-0017 »*,
  et c'est le contrôle de l'atlas qui l'a rattrapé). Le nombre vit là où vit la donnée qui le
  détermine : les braquets pour un tableau, `EtatSuisse` pour un suisse, `EtatPoules` pour des
  poules.
- `backend/domain/suivi_deroule.py` — `AvancementBloc` porte désormais un tour courant **générique**,
  découplé de `TourBraquet` ; c'est ici que la séparation « avancer ≠ classer » est tenue.
- `backend/application/suivi_deroule.py` — `LecteurAvancementDePhase` (le port) et sa consommation
  par `ServiceSuiviDeroule`.
- `backend/application/poules.py`, `application/suisse.py`, `application/big_shoot_off.py` — les
  réalisations du port, une par format qui déroule.
- `backend/bootstrap/composition.py` — les branchements par type.
