# ADR-0066 — Le seuil de barrage est porté par la politique `tiebreak`

- **Statut** : Accepté
- **Date** : 2026-08-02
- **US** : E06US003 — Barrage de tir pour places décisives
- **Révise** : la signature de `tiebreak` d'[ADR-0004](0004-politiques-injectables.md) (une méthode → deux)

## Contexte

E06US001 a livré le classement de qualification avec le départage FFTA (§8.1 : plus de 10, puis de
9) et a **laissé une porte ouverte** : « si l'égalité subsiste, le défaut est l'ex æquo ; départager
les places à enjeu par un **barrage** de tir (§8.2) reste une **option configurable** — les deux
résolutions doivent rester ouvertes ».

E05US015 a livré le **moteur** du barrage (`domain/barrage.py`), pur et complet : absents relégués
(B.6.5.2.4) → plus haut score → distance au centre → groupes à rejouer. Il n'avait **aucun
appelant** : `resoudre_barrage` départage des tirs déjà clos, mais rien ne décidait *quand* faire
tirer, ni *quoi faire* du verdict. C'est une part de [DETTE-028](../dette.md).

Le CA d'origine d'E06US003 tenait en une ligne — « déclenchement d'un barrage pour les positions à
enjeu ; résultat intégré au classement ». **Deux mots y étaient indéterminés** : « positions à
enjeu » (lesquelles ? décidées par qui ?) et « intégré » (à quel prix pour les rangs voisins ?). Le
cadrage du 02/08/2026 avec le commanditaire a tranché : seuil **configurable**, déclenchement
**automatiquement signalé**, persistance **flèche par flèche**.

Restait la question de conception : **où vit le seuil ?**

## Décision

### 1. Le seuil est un réglage de format, donc une politique

Ce qui fait qu'une place est « à enjeu » dépend du tournoi : la dernière place qualificative d'un
tableau de 8 n'est pas celle d'un tableau de 32, et un club peut vouloir ne barrer que le podium.
C'est exactement ce qu'ADR-0004 appelle de la **configuration**, pas du code.

La famille concernée est sans ambiguïté `tiebreak` : le seuil dit *jusqu'où* on départage, le
comparateur dit *comment*. Nous l'y logeons plutôt que d'ouvrir une **septième famille**, pour une
raison qui n'est pas l'économie : les deux réglages doivent rester **cohérents entre eux**. Barrer
selon §8.1 dans un tournoi qui départage en poule (§10.1, cinq critères) n'a aucun sens, et deux
familles séparées permettraient précisément de les désaccorder — un formulaire, deux menus, aucune
contrainte croisée.

Concrètement, une nouvelle implémentation composite, sur le patron de `RoutingRepechage` :

```json
{ "policies": { "tiebreak": { "nom": "barrage", "jusqu_au": 8, "sinon": { "nom": "ffta_defaut" } } } }
```

`TiebreakAvecBarrage` **délègue** `departager` à son `sinon` sans y toucher, et n'ajoute que le
déclenchement. Un seuil réglé sur `TiebreakPoules` départage donc toujours en poule : les deux
réglages voyagent ensemble, c'est ce qui les garde accordés.

`jusqu_au` est **obligatoire** (comme le `tours` du repêchage) : un barrage sans seuil est un
`ffta_defaut` déguisé, et l'accepter laisserait croire à l'organisateur que son format départage au
tir alors qu'il n'en fait rien. Un barrage **ne s'enveloppe pas lui-même** — deux seuils imbriqués
ne composent rien, le plus interne serait purement ignoré (`barrage_requis` n'est jamais délégué) ;
refusé explicitement plutôt que laissé à une limite de profondeur, ce qui le distingue du repêchage
dont l'imbrication, elle, aurait un sens.

### 2. Le protocole `Tiebreak` gagne une seconde méthode

`Tiebreak` passe de `departager(a, b) -> int` à ce comparateur **plus** `barrage_requis(rang) ->
bool`. Les deux implémentations historiques (`TiebreakFftaDefaut`, `TiebreakPoules`) renvoient
`False` : le défaut du produit reste l'ex æquo partagé, et E06US001 est **inchangée** tant que rien
n'est réglé.

⚠️ **Cela ne contredit pas l'arbitrage d'E05US015**, qui écrivait : « un comparateur pur ne peut
pas faire tirer des flèches ; il constate l'ex æquo, et c'est au moteur de décider s'il organise un
barrage ». `barrage_requis` **ne fait tirer personne** : elle constate qu'une place mérite d'être
tranchée. Le partage des rôles est intact — la politique constate, le service organise,
l'organisateur déclenche.

**Prix assumé** : toute implémentation de `Tiebreak` porte désormais deux méthodes, dont une triviale
pour les deux stratégies existantes.

**Alternative écartée** : lire le seuil par `isinstance(tiebreak, TiebreakAvecBarrage)` dans le
moteur. C'est un test de type au runtime, c'est-à-dire exactement ce qu'un protocole existe pour
éviter — et il aurait fallu le refaire à chaque nouveau consommateur.

### 3. Le seuil désigne le rang du **groupe**, pas chacune de ses places

Deux ex æquo au rang 8 avec `jusqu_au = 8` se départagent, et le barrage tranche donc **aussi** la
9ᵉ place, située au-delà du seuil.

Ce n'est pas un effet de bord toléré, c'est le cas d'usage : « départager la dernière place
qualificative » est **par construction** une égalité qui chevauche le seuil. Le lire place par place
rendrait l'option inutile là précisément où on la demande.

### 4. Le verdict n'est pas stocké : il se recalcule depuis les tirs

La persistance est au grain **(barrage, manche, archer)**. Aucune colonne ne porte l'ordre obtenu :
`BarrageDePlaces.resultat()` le recalcule à chaque lecture. C'est ce qui rend une flèche mal notée
**corrigeable** — la corriger corrige le classement. Stocker l'ordre à côté des tirs créerait deux
vérités, dont une périmée dès le premier correctif. Le port lui-même n'expose donc **aucune** méthode
qui rendrait « le verdict » : l'offrir inviterait à le mémoriser.

Corollaire : `partitionner_barrage` est exposé à côté de `resoudre_barrage`. Ce dernier interdit
l'ordre partiel (« un classement à moitié vrai est plus dangereux qu'un refus »), donc il rend
`groupes_a_rejouer` **sans** l'ordre relatif des groupes. Juste pour qui publie un résultat,
insuffisant pour la **répétition en manches**, qui doit savoir que le groupe à 10 précède celui à
8 — sans quoi un retir ferait passer un tireur à 8 devant un tireur à 10 déjà départagé. On expose
la partition à côté plutôt que d'affaiblir un contrat pour un seul appelant.

### 5. Ce que le barrage change au classement, et ce qu'il ne change pas

Le verdict n'intervient **qu'après** épuisement de la politique de départage — c'est-à-dire
exactement là où le rang serait resté partagé. Il rend les rangs **consécutifs** sans décaler les
suivants (un barrage éclate un rang partagé, il n'insère personne : trois ex æquo au 8 deviennent
8, 9, 10 et le suivant reste 11ᵉ), et il tranche les **deux** rangs — scratch et catégorie —,
l'ordre étant commun. Laisser le rang de catégorie partagé pendant que le scratch est tranché
produirait un classement cohérent en apparence et contradictoire à l'impression du podium.

Au passage, `domain/classement.py` cesse de réimplémenter §8.1 à la main et passe par
`PolitiquesPhase.tiebreak` : c'est la couture qu'E06US001 avait annoncée et que DETTE-028 réclamait.
Le tri devient un **comparateur** (`cmp_to_key`) et non plus une clé, parce qu'une politique
injectable rend un ordre relatif — il n'existe aucune clé qui exprimerait les cinq critères de poule
et les deux de la qualification sans les figer, ce que l'injection sert justement à éviter.

## Conséquences

**Positives.**
- L'option laissée ouverte par E06US001 est **fermée sans changer le défaut** : un tournoi qui ne
  règle rien se comporte exactement comme avant, ce qu'un test fixe explicitement.
- Le moteur d'E05US015 a enfin des consommateurs, et une part de DETTE-028 est résorbée.
- Le seuil vit dans `config.policies`, donc il voyagera avec les **formats** (E01US023/E01US024)
  sans travail supplémentaire le jour où l'écran « Composer un déroulé » l'exposera.

**Négatives / à surveiller.**
- **Une seule des trois portées est câblée.** `PorteeBarrage` modélise qualification, poule et Big
  Shoot Off, et le moteur les sert toutes les trois ; mais ni `poule.py` ni `big_shoot_off.py` n'ont
  de **consommateur de production** (DETTE-028, vérifié dans le code et non supposé) : il n'existe
  aucun classement de poule calculé quelque part où brancher un barrage. Les câbler aurait produit
  une surface pour une phase que l'application ne sait pas dérouler. Le discriminant est en base dès
  maintenant pour éviter une migration de données le jour venu.
- **Le `PUT` de phase est une édition totale** : omettre `barrage_jusqu_au` **efface** le seuil.
  C'est le régime déjà annoncé pour `sources` (et la raison de son `extra="forbid"`), mais il vaut
  désormais pour un réglage de plus.
- **Deux modèles du même article règlementaire coexistent.** Le shoot-off *interne* à un duel nul
  vit dans `domain/duel.py` (`Barrage` : deux flèches `ZoneScore`, vainqueur **désigné à la main**,
  l'application ne mesure pas), séparément de celui-ci (`TirBarrage` : score entier, **distance
  mesurée** en dixièmes de mm). ADR-0049 §3 avait délibérément tranché cette séparation et nous ne
  la rouvrons pas — mais elle mérite d'être connue : deux écrans font tirer « un barrage » et n'en
  demandent pas la même chose. C'est aussi pourquoi l'agrégat de cette US s'appelle
  `BarrageDePlaces` et non `Barrage` : deux classes homonymes pour deux notions que le projet
  distingue exprès auraient été un piège de relecture, d'autant qu'elles se croisent dans
  `repositories.py`.
- **Le `barrage_requis` du protocole et le `barrage_requis` de `ResultatDuel`** portent le même nom
  dans deux espaces distincts, avec des sens voisins mais non identiques (« cette place mérite un
  tir » vs « ce duel est nul »). Sans conflit technique, mais à ne pas confondre en lecture.

## Alternatives écartées

| Alternative | Pourquoi non |
|---|---|
| Une **7ᵉ famille** de politique (`barrage`) | Deux réglages qui doivent rester accordés deviendraient désaccordables ; un booléen ne justifie pas une famille |
| Le seuil **en dur** (« on barre toujours le podium ») | Le CA le voulait configurable, et « à enjeu » n'a pas de définition indépendante du format |
| Le seuil sur le **tournoi** plutôt que la phase | Le départage est une propriété de la phase qui classe (une qualification et une poule ne barrent pas aux mêmes places) |
| `Phase` porte la `config.policies` **brute** | L'agrégat porte des réglages **typés** (`bareme`, `validation`), jamais un dictionnaire d'infrastructure — règle 4 |
| **Stocker le verdict** en base | Deux vérités, dont une périmée au premier correctif de flèche ; et plus aucune façon de corriger une saisie |
| Enregistrer les tirs **flèche par flèche** | Exposerait une manche incomplète à la lecture, donc un verdict provisoire faux ; un barrage se tire d'un bloc |
