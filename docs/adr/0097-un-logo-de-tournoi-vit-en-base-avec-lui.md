# ADR-0097 — Un logo de tournoi vit en base avec lui, et deux accents suffisent à en dériver le chrome

- **Statut** : Accepté
- **Date** : 2026-08-25
- **US** : E16US006 (absorbe E01US016)
- **Décideurs** : Organisateur / Architecte
- **S'appuie sur** :
  - [ADR-0074](0074-la-charte-mesuree-du-club-en-jetons.md) — la charte mesurée en jetons, dont cet
    ADR reprend la **règle de dérivation** pour l'automatiser
  - [ADR-0026](0026-cycle-de-vie-du-tournoi-sept-statuts.md) §1 — `archivé` = lecture seule totale,
    la seule garde de statut que l'identité oppose
- **Voisin** : [ADR-0060](0060-briques-du-patrimoine-du-club-bibliotheque-copie-promotion.md) —
  l'identité **n'est pas** une brique de patrimoine : elle ne se copie ni ne se promeut, elle
  appartient à une édition et meurt avec elle

> ⚠️ **Cet ADR ne figure pas à la liste nominative d'[ADR-0075 § « Portée de la règle »](0075-le-depart-est-la-portee-sportive.md#portée-de-la-règle--porté-dans-le-code-par--tranchée-le-08082026), et c'est volontaire.**
> Il est d'**IHM et de stockage d'actif** : le moteur sportif ne lit aucune couleur, aucune portée ne
> change, aucune politique injectable n'est en jeu. Le critère de `CLAUDE.md` exclut nommément les
> ADR d'UI et d'outillage ; les précédents existent (`0086`, `0088`, `0095`, `0096`). Il porte en
> revanche sa section « Porté dans le code par », exigée de **tout ADR neuf** sans condition.
>
> *(Noté explicitement, sur le précédent d'ADR-0095 et d'ADR-0096 : un trou **non commenté** dans
> cette liste est précisément ce qui produit l'omission suivante — quatre l'ont déjà été.)*

## Contexte

Le club a **deux marques** : *Les Archers de Kervignac*, permanente, et l'événement — *Challenge des
Champions* — qui change à chaque édition. Deux demandes convergeaient vers cette US :

> A05 : *« ajouter un champ de plus pour le logo du club qui organise le tournoi, en plus du logo du
> tournoi ; bien sûr cela reste optionnel »*

> `DV-06` (CDC design §3.6, ferme `Q-D8`) : *« identité par tournoi = logo + 2 accents, le système
> dérive tout le reste ; 3 strates de tokens — marque personnalisable, sémantique et structure
> figées »*

`E16US006` demandait « un second logo », mais **le premier n'existait pas** : `E01US016` (l'identité
visuelle) était ⬜, et `grep -i logo backend/` rendait zéro occurrence. `EPIC-17` l'avait d'ailleurs
noté sans que la conséquence en soit tirée : *« A05 · identité : l'écran n'existe pas, ce n'est pas
un écart de fidélité, c'est une US non livrée »*. Le cadrage du 25/08/2026 a donc **fusionné les
deux** — livrer un second logo sans le premier n'avait pas de sens.

Trois questions restaient ouvertes, toutes tranchées par le commanditaire ce jour-là.

## Décision

### 1. Les octets d'un logo vivent **en base**, dans une table à part

Le fichier est stocké en blob dans `identite_tournoi`, servi par une route dédiée. L'alternative —
un répertoire d'actifs sur le disque, chemin en base — a été écartée sur **trois conséquences
concrètes**, pas sur une préférence :

- **sauvegarder, le jour J, c'est copier le `.db`.** Un logo sur le disque en sortirait, et la
  sauvegarde deviendrait deux gestes dont l'un s'oublie ;
- **supprimer un tournoi supprime sa descendance.** Un fichier orphelin, non ;
- **`EPIC-11` promet une archive en lecture seule.** Un fichier reste remplaçable sous les pieds du
  tournoi archivé ; une ligne de base, non.

Le prix est réel et assumé : des octets passent par la **file d'écriture unique** (règle 7). Il est
borné par `POIDS_LOGO_MAX_OCTETS` (512 Ko), et déposer un logo est un geste de **préparation**,
jamais un chemin chaud du jour J.

**Une table distincte, pas six colonnes sur `tournoi`.** La ligne `tournoi` est lue partout — liste
des tournois, tableau de bord, toute lecture publique. Y poser deux blobs les ferait traîner à
chaque fois. La clé primaire **est** la clé étrangère : « au plus une identité par tournoi » est tenu
par le schéma. Et l'adapter va plus loin en séparant les **lectures** : une projection sans blob pour
les réglages, une requête par logo pour les octets.

### 2. Le fichier est fourni **déjà calibré** — l'application refuse, elle ne répare pas

`Q-UX10` (« qui produit le logo — un SVG de graphiste ou un JPEG de téléphone à recadrer ? ») est
close : **un fichier propre**. SVG ou PNG, 512 Ko au plus, utilisé tel quel. Ni recadrage, ni
détourage, ni redimensionnement — donc **aucune dépendance de traitement d'image** (règle 11). Ce
que l'application n'accepte pas, elle le **refuse en le disant**, plutôt que de laisser croire
qu'elle a traité le fichier.

⚠️ **Un SVG est un document, pas une image.** Servi depuis l'origine de l'application — celle qui
sert aussi la SPA d'administration —, un SVG porteur de script s'exécuterait avec la session de qui
l'ouvre. Trois barrières, dans cet ordre :

1. le **domaine refuse** au dépôt ce qui exécute — `<script>`, gestionnaire `on…`, URL `javascript:`
   et `<foreignObject>` (qui réintroduit du HTML dans le SVG). Ne bloquer que la balise donnerait un
   garde-fou qui rassure sans protéger ;
2. la **route** sert le fichier sous `Content-Security-Policy: default-src 'none'`,
   `X-Content-Type-Options: nosniff` et `Content-Disposition: inline` — la barrière qui tient si un
   fichier est entré sous une version antérieure des règles ;
3. le **rendu** passe par `<img>`, qui neutralise les scripts.

Le **contenu fait foi, pas le type annoncé** : un fichier déclaré PNG mais contenant du balisage est
refusé.

### 3. Deux accents, et la dérivation vit dans le **domaine**

« Teinte et saturation conservées, clarté ajustée jusqu'au seuil AA » (`DV-05`) est une **règle
reproductible** : une entrée, une sortie, aucune horloge, aucun aléa. Elle est donc du domaine pur
(règle 1), et non un calcul recopié dans le navigateur, où il aurait échappé à `mypy --strict` et
n'aurait été vérifié par personne. Le front reçoit des **valeurs prêtes à poser**.

⚠️ **L'oracle de cette dérivation n'a pas été inventé pour l'occasion.** `frontend/src/index.css`
(E17US001, ADR-0074) décline le rouge `#B71918` **à la main** en `#CC1C1B` (contour, 3,01:1) et
`#E84E4D` (texte, 4,52:1). Vérification faite en écrivant les tests, ces trois valeurs conservent
teinte et saturation à moins d'un demi-degré près : la charte avait déjà appliqué la règle que ce
module automatise. Le contour est **reproduit exactement** ; le texte tombe **un cran plus bas**
(`#E84D4D`, 4,50:1), parce que la charte s'était arrêtée un pas après le franchissement là où
`DV-05` demande d'ajuster **jusqu'au** seuil — donc de toucher la marque le moins possible. Les deux
sont conformes ; l'écart est instruit et testé dans les deux sens.

**Ce que les accents ne touchent PAS**, et c'est le verrou : les jetons de **marque**, jamais le fond
de page ni les couleurs sémantiques. Le CDC l'écrit en deux verrous — *« alerte, succès, info
appartiennent au produit, pas au tournoi »* (`DV-03`) et *« les neutres, l'échelle typographique, les
espacements et les composants ne bougent pas »*. Ce n'est pas de la prudence : `index.css` mesure
**chaque** couleur contre `--surface-0`. Repeindre le fond par tournoi invaliderait d'un coup les
vingt ratios de la charte, sans qu'aucun test ne bouge.

### 4. « Hériter » et « avoir choisi » sont **deux états distincts**

Le CA dit « défaut = identité du club **si rien n'est fourni** ». Les accents sont donc `NULL` tant
que personne n'a choisi, et `reglee` s'en **dérive** — l'écran peut alors dire *hérité* plutôt que
d'afficher un formulaire vierge, et un tournoi dont on a seulement déposé le logo ne se présente pas
comme configuré.

⚠️ **La première rédaction faisait circuler un booléen `reglee` de la persistance jusqu'au DTO**, à
côté d'une identité toujours concrète. Un test d'API l'a démentie : déposer un logo crée la ligne, et
la relecture annonçait « réglée » sans qu'aucune couleur ait été choisie. Deux sources pour un même
fait, dont l'une réécrite à la main à chaque appel. Il n'en reste qu'une — une valeur absente.

### 5. Portée : le public et l'écran de salle, **jamais** l'admin ni la saisie

`D-27` : *« le jour J, un bénévole n'a pas le temps de réapprendre des repères visuels »*. Ce n'est
pas tenu par une condition mais par le **montage** : le composant d'habillage n'est monté que dans
`EcranSalle` et dans les vues publiques d'un tournoi. Un `if` aurait été un endroit de plus où se
tromper ; une coquille qui ne l'appelle pas ne peut pas le porter par accident.

L'habillage est posé sur les **vues d'un tournoi choisi**, pas à la racine de la coquille publique :
la liste des tournois n'appartient à aucune édition, l'habiller aux couleurs de la première l'aurait
fait mentir.

### 6. L'identité **n'est pas une brique de patrimoine** (ADR-0060)

Elle ne se copie pas d'un tournoi à l'autre, ne se promeut pas dans une bibliothèque, et n'a pas
d'`OrigineBrique`. Un logo d'édition change **par définition** à chaque édition ; le logo du club,
lui, est stable — mais le stocker une fois pour toutes créerait un actif du club à gérer, pour un
gain nul (il se redépose en un clic). C'est la seule dissymétrie assumée avec ADR-0060, et elle
tient à ce que l'identité **est** ce qui distingue une édition.

## Conséquences

- **Une migration** (`0050`) et une table neuve. Elle ne peuple **rien** : semer une ligne par
  tournoi existant aurait matérialisé un défaut en donnée, et rendu indiscernables les deux états du
  §4.
- **Deux lectures publiques** : l'identité déclinée et les octets d'un logo. Il n'y a rien à protéger
  dans une couleur projetée sur le mur d'un gymnase, et l'écran de salle n'a pas de session admin.
- **Un logo monte en corps brut**, pas en `multipart/form-data` : `UploadFile` aurait exigé
  `python-multipart`, ni installé ni déclaré — un arbitrage de dépendance (règle 11) pour téléverser
  un fichier sans aucun champ à côté. Bonus sur un réseau de gymnase : pas les ~33 % d'inflation
  d'un base64.
- **Deux jetons de marque neufs par thème** (`--brand-2-*`, `--sur-brand-2`) dans `index.css` : la
  charte décrit deux accents depuis `DV-06`, un seul existait. ⚠️ **Leur usage reste volontairement
  mince** — l'accent secondaire est posé et disponible, mais aucune planche ne dit encore ce qu'il
  doit peindre. Inventer sa place aurait été du design, pas de l'implémentation ; c'est signalé
  plutôt que comblé.
- **`charte.test.ts` est étendu, pas relâché.** Son contrôle « aucune feuille de feature ne redéfinit
  un jeton » est écrit pour du CSS : appliqué à un `.ts` qui **fabrique** du CSS en chaîne de
  gabarit, il ne voyait rien. La réponse n'a pas été d'élargir une dérogation mais d'encoder la règle
  qui manquait — les **trois strates** de `DV-06` —, vérifiée par mutation dans les deux sens.
- **`E01US016` est absorbée** : elle disparaît du reliquat et son CA est livré ici en entier, à une
  réserve près (l'usage de l'accent secondaire, ci-dessus).
- **L'empreinte du contenu de chaque logo est PERSISTÉE, et elle adresse l'image.** Décision prise
  en revue, après deux rédactions cassées. Le besoin : rendre un logo **remplacé** visible sans
  rechargement. Une URL stable ne provoque aucune requête sur une image déjà montée (React ne
  réécrit pas un attribut inchangé, donc `Cache-Control: no-cache` ne s'applique à rien) ; une URL
  versionnée par l'horodatage de la requête change à **chaque** événement WebSocket et retélécharge
  512 Ko pour rien. Seule une valeur qui suit les **octets** tient les deux bouts.

  Elle est **stockée** (deux colonnes) plutôt que recalculée, parce que l'argument du §1 vaut ici :
  hacher 512 Ko pour connaître un numéro de version annulerait la projection sans blob que la table
  séparée existe pour permettre — sur la route la plus chaude, où le `304` est la réponse ordinaire.
  Elle sert donc à la fois d'`ETag` et de segment `?v=`, lus de la **même** colonne : une seule
  source pour la version.

  **Prix assumé** : une valeur dérivée en base, dont l'adapter est le seul écrivain, et un invariant
  qui passe de deux à trois colonnes que SQLite ne sait pas exprimer. Les deux sont tenus par
  `IdentiteVisuelleRepositorySQL` et vérifiés par `test_identite_repository.py`, qui refuse une
  ligne où présence et empreinte divergent.
- **`Q-UX10` est fermée** (§2). **`Q-UX11`** (« une archive fige-t-elle son identité ? ») l'est **par
  construction** : les octets vivent dans la ligne du tournoi, et `archivé` refuse toute écriture.
- **L'argument « supprimer un tournoi supprime sa descendance » (§1) est tenu par une cascade
  explicite, pas par la promesse d'ADR-0077.** C'est une correction de revue, et elle est
  structurante : la table avait d'abord été posée avec une clé étrangère **nue**, marquée
  `DETTE-001` par application mécanique de la procédure d'aggravation de ce registre. Mais la ligne
  d'identité naît au premier réglage et n'est jamais retirée : sous `PRAGMA foreign_keys=ON`, le
  tournoi devenait **définitivement** indéracinable (500), et l'argument central de cet ADR se
  trouvait démenti par la table qu'il justifie. `identite_tournoi` est un **composant strict** de
  l'agrégat — une ligne, sans descendance, cosmétique — donc du même genre que `volee` et
  `placement`, qui cascadent déjà et sont hors DETTE-001. Cf. la section de détail de DETTE-001
  dans [`docs/dette.md`](../dette.md), qui porte la leçon de méthode.

## Porté dans le code par

⚠️ **Ce tableau a été corrigé à TROIS passes de revue, et la récidive est plus instructive que le
défaut.**

1. La première rédaction attribuait §5 (la portée) à `HabillageIdentite.tsx`. Or ce module est ce
   **qui est monté**, pas ce **qui décide où** : le montage vit chez ses appelants, et rien
   n'empêchait une US future de l'importer dans l'admin — la décision était appliquée sans être
   gardée, exactement le mode de panne d'ADR-0017
   qu'[ADR-0075](0075-le-depart-est-la-portee-sportive.md) existe pour ne pas rejouer.
2. La correction a rendu la ligne de `application/identite.py` fausse à son tour, en la faisant
   renvoyer à un « §3 (`P-4`) » — alors que `P-4` n'apparaît nulle part dans cet ADR et que §3 ne
   décide rien sur le caractère non bloquant du contraste.
3. Et la suivante a laissé la ligne du repository attester l'invariant « les **deux** colonnes d'un
   logo » que le même commit venait de porter à trois.

Trois fois le même défaut, dans la même table, chaque fois dans le commit qui prétendait le réparer.
Ce qui manquait n'est pas l'attention : c'est un **geste**, et il tient en une phrase — *rouvrir
cette table, c'est relire chacune de ses lignes contre le diff du jour*, la section citée comprise,
pas seulement celle qu'on vient de corriger.

Le garde-fou de portée manquant a été écrit dans le même mouvement. La leçon est celle qu'ADR-0075
inscrit déjà : **cette section s'écrit en vérifiant dans le code du jour, pas en déduisant de
l'ADR** — nommer un module qui « devrait » porter la décision reproduit le défaut au lieu de le
prévenir.

| Module | Ce qu'il tient de cet ADR |
|---|---|
| [`frontend/src/features/identite/api.ts`](../../frontend/src/features/identite/api.ts) (`urlDuLogo`) | § Conséquences l'adresse d'un logo versionnée par l'**empreinte de son contenu** — ni URL stable (aucune requête sur une image déjà montée), ni horodatage de cache (une URL neuve à chaque événement WebSocket) |
| [`backend/domain/identite.py`](../../backend/domain/identite.py) | §3 la dérivation (pure, teinte et saturation conservées) et ses deux seuils WCAG ; §2 le refus de contenu d'un logo ; §4 `IdentiteVisuelle` à accents facultatifs et `reglee` dérivé |
| [`backend/application/identite.py`](../../backend/application/identite.py) | §3 la **déclinaison servie prête à poser** — les deux thèmes calculés côté serveur (`decliner`), le front ne recalcule rien. *(Deux autres décisions passent par ce module sans venir de cet ADR : le contraste rendu comme chiffre et non opposé comme refus vient de `P-4` ; le verrou d'archive, d'ADR-0026 §1.)* |
| [`backend/api/v1/identite.py`](../../backend/api/v1/identite.py) | §1 la route qui sert les octets ; §2 les trois en-têtes de sûreté et le corps brut ; §5 les deux lectures publiques |
| [`backend/infrastructure/db/repositories/referentiel.py`](../../backend/infrastructure/db/repositories/referentiel.py) (`IdentiteVisuelleRepositorySQL`) | §1 la projection **sans blob** des réglages (empreintes + présence, jamais les octets), l'invariant « les **trois** colonnes d'un logo — octets, type, empreinte — ou aucune », et la lecture de la seule empreinte qui permet à la route des octets de répondre `304` sans les charger |
| [`backend/migrations/versions/0050_identite_visuelle_tournoi.py`](../../backend/migrations/versions/0050_identite_visuelle_tournoi.py) | §1 la table à part **et sa cascade** (`ON DELETE CASCADE`, sans laquelle l'argument « supprimer un tournoi supprime sa descendance » du §1 serait faux) ; §4 les accents nullables et l'absence de peuplement |
| [`frontend/src/features/identite/jetons.ts`](../../frontend/src/features/identite/jetons.ts) | §3 les seuls jetons de **marque** émis, dans les trois déclinaisons de thème |
| [`frontend/src/features/identite/HabillageIdentite.tsx`](../../frontend/src/features/identite/HabillageIdentite.tsx) | le mécanisme d'habillage lui-même : pose les jetons, rend les deux logos facultatifs |
| [`frontend/src/features/salle/EcranSalle.tsx`](../../frontend/src/features/salle/EcranSalle.tsx) et [`frontend/src/features/public/AccueilPublic.tsx`](../../frontend/src/features/public/AccueilPublic.tsx) | §5 la portée, qui tient à leur **montage** — ce sont eux qui l'appliquent, et eux seuls |
| [`frontend/src/shared/charte.test.ts`](../../frontend/src/shared/charte.test.ts) | §3 le garde-fou des trois strates **et** §5 celui de la portée (les seuls importateurs autorisés de l'habillage) — c'est lui qui **vérifie** que cet ADR est tenu |
