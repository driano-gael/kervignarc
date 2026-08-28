# ADR-0099 — Le code porte des **pointeurs**, pas le raisonnement

- **Statut** : Accepté
- **Date** : 2026-08-27
- **US** : `E00US027`
- **Décideurs** : Organisateur / Architecte

> ⚠️ **Cet ADR ne figure pas à la liste nominative d'[ADR-0075 § « Portée de la règle »](0075-le-depart-est-la-portee-sportive.md#portée-de-la-règle--porté-dans-le-code-par--tranchée-le-08082026), et c'est volontaire.**
> Il est de **convention documentaire** : aucun moteur sportif ne lit une convention de commentaire,
> aucune portée ne change, aucune politique injectable n'est en jeu. Le critère de `CLAUDE.md` exclut
> nommément ce cas ; les précédents sont `0086`, `0088`, `0089`, `0095`, `0096`, `0097`, `0098`. Il
> porte en revanche sa section « Porté dans le code par », exigée de **tout ADR neuf** sans condition.

## Contexte

Le commentaire est, dans ce dépôt, le seul artefact que **rien ne vérifie** : ni le compilateur, ni
`mypy`, ni `eslint`, ni un test. Une phrase fausse y survit indéfiniment, et elle est lue comme une
preuve.

Mesure du 27/08/2026, sur le code de **production** (tests exclus) :

| Périmètre | Lignes | Commentaire | Part | Fichiers ≥ 40 % |
|---|---|---|---|---|
| Backend | 68 074 | 28 085 | **41 %** | **103** |
| Front | 40 044 | 11 121 | **28 %** | 48 |
| **Total** | **108 118** | **39 206** | **36 %** | **151** |

⚠️ **Une première mesure annonçait 13 %, et elle était fausse d'un facteur trois** : elle comptait
les lignes commençant par `#` ou `//` et ne voyait donc **aucune docstring Python** — c'est-à-dire
la forme sous laquelle ce dépôt documente presque tout son backend. La bonne mesure passe par
`tokenize`, pas par un `grep`. *(Le premier jet de cet ADR portait le chiffre faux ; corrigé le jour
même, sur la question du commanditaire « je ne vois pas le nettoyage côté back ». Il avait raison :
le backend n'avait pas été omis par choix, il n'avait jamais été mesuré.)*

Ce n'est donc pas un excès marginal : **plus d'un tiers du code de production est de la prose**. Et
en lisant ce que contiennent réellement ces fichiers, le volume ne vient pas de ce qu'on croit :

| Ce qu'on y trouve | Ce que c'est | Où ça vit déjà |
|---|---|---|
| « relevé en 2ᵉ passe, axe C2 », « la 1ʳᵉ rédaction disait X » | de l'**historique de revue** | `git log`, corps de commit |
| Le questionnaire P06 recopié mot pour mot sur huit lignes | un **CA** | [`stories/`](../../stories/) |
| Le raisonnement complet d'un arbitrage, sur vingt lignes | une **décision** | l'ADR correspondant |
| « pourquoi ce module a été créé en E01US024 » | de l'**archéologie** | `docs/dette.md`, `git log` |
| « ce 3 vient de `columns: 3 22ch` dans `salle.css` » | une **contrainte invisible** | **nulle part ailleurs** |

Seule la dernière ligne justifie sa place dans le code. Les quatre autres sont des **copies** — et
une copie diverge. C'est le mécanisme qui a produit, en revue d'`E16US009`, une section d'ADR
nommant un test inexistant, un renvoi de dette pointant la mauvaise entrée, et trois commentaires
sur-promettants réécrits trois fois.

**La maxime « un code qui a besoin de commentaires se lit mal » est vraie aux deux tiers**, et c'est
la nuance qui décide de cet ADR. Elle vaut pour le **quoi** (un commentaire qui paraphrase est un
échec de nommage) et pour le **comment** (un commentaire qui explique l'algorithme est un échec de
découpage). Elle est **fausse pour le pourquoi** : aucun nommage, si bon soit-il, ne peut dire qu'une
constante dérive d'une règle CSS écrite dans une autre feature. `NOMS_PAR_LIGNE_PROJETEE = 3` est
parfaitement nommé et reste indéchiffrable sans cette phrase.

Le pourquoi doit donc exister — la question est **où**.

## Décision

**Le code porte des pointeurs vers le raisonnement, il ne le recopie pas.** Un commentaire ne
survit que s'il satisfait **au moins un** de ces trois tests :

1. **Contrainte non déductible du fichier** — un couplage que rien n'exprime dans le langage : une
   valeur qui dérive d'un autre fichier, un invariant tenu ailleurs, un ordre d'exécution imposé.
2. **Avertissement** — une modification d'apparence innocente casserait quelque chose, et le code ne
   peut pas le dire seul (le repli d'un ternaire qui rend un oubli compilable, un effet de bord au
   démontage, une garde dont dépend une autre couche).
3. **Renvoi** — une ligne qui nomme l'ADR, la story ou l'entrée de dette qui porte le raisonnement.
   **Une ligne**, pas le raisonnement recopié.

Tout le reste sort : historique de revue, citations de CA, justification d'existence, paraphrase du
code, narration de processus.

### Amendement du 27/08/2026 — trois contraintes de forme, parce que le jugement seul ne suffit pas

Les trois tests ci-dessus reposent sur une appréciation, donc **rien ne les contrôle**. Mesuré sur
trois vagues et onze fichiers : **122 lignes retirées sur 39 206, soit 0,3 %** — le pourcentage
global n'a pas bougé d'un point. Le tri sémantique plafonne, parce que l'essentiel du volume est
fait d'avertissements et de contrats que la règle protège à raison.

S'y ajoutent donc deux contraintes de **forme**, qui priment sur le jugement, et un **indicateur** :

1. **Huit lignes au plus par bloc de commentaire.** Au-delà, ce n'est plus un avertissement mais un
   raisonnement : il part en ADR, en story ou au registre, et le code garde **un renvoi**. Huit
   lignes suffisent à énoncer un piège ; elles ne suffisent pas à le justifier — et c'est
   exactement la frontière qu'on cherche.
2. **Aucune docstring tautologique.** Si elle ne dit rien de plus que la signature, elle disparaît.
3. **Un seul avertissement par bloc — indicateur de revue, non mécanisé** *(reclassé en revue de
   la 2ᵉ passe d'E00US027, 28/08/2026)*. Trois ⚠️ empilés signalent un module qui fait trop de
   choses ou un raisonnement à sortir, mais **la contrainte (1) pousse en sens inverse** : fusionner
   pour tenir en huit lignes empile les avertissements. E00US027 s'est livrée en violant ce point
   **153 fois**, et le volume de ⚠️ a **augmenté** malgré la coupe. Une règle démentie par son propre
   commit d'introduction ne se tient plus jamais : on la relève à la lecture, on ne la compte pas.

**Pourquoi le plafond, et pas une quatrième règle de jugement** — c'est le point de cet amendement.
Le plafond est la **seule règle de commentaire du projet qui se compte**. Elle peut donc devenir un
test, appliqué aux fichiers d'un diff, au même titre que le garde-fou d'isolation du domaine ou les
contrôles d'atlas. Tout ce que cette US a appris tient dans cette phrase : **ce qui est vérifié ne
diverge pas** — et le commentaire n'avait, jusqu'ici, aucun garde-fou d'aucune sorte.

Gisement mesuré au moment de l'amendement, côté backend (28 006 lignes de commentaire, 4 370 blocs) :

| Plafond | Blocs au-dessus | Lignes en excédent | Part du commentaire |
|---|---|---|---|
| 12 lignes | 610 | 4 985 | 18 % |
| **8 lignes** *(retenu)* | **1 051** | **8 469** | **30 %** |
| 5 lignes | 1 934 | 13 116 | 47 % |

⚠️ **Le plafond DÉPLACE, il ne supprime pas.** Ce qui sort d'un bloc trop long doit atterrir quelque
part — la règle de sécurité ci-dessous ne souffre aucune exception, et elle coûte plus cher à
appliquer qu'à écrire. Un plafond tenu en jetant du savoir serait pire que pas de plafond.

### La règle de sécurité, qui prime sur tout le reste

⚠️ **On ne coupe que ce qui existe ailleurs.** Avant de retirer une phrase, on vérifie qu'elle est
portée par un ADR, une story, le registre de dette ou un test. Si elle n'est nulle part, **on la
déplace d'abord** — le nettoyage ne détruit aucune connaissance, il la range.

C'est le seul vrai risque de cette décision, et il est asymétrique : un commentaire de trop coûte
une lecture, un savoir perdu coûte une US.

### Ce que la décision ne dit pas

- **Ce n'est pas une chasse au commentaire.** Un fichier à 60 % peut être légitime si la règle
  métier qu'il porte est subtile — `shared/phases/relance.ts` en est un candidat. Le pourcentage
  **désigne où regarder**, il ne condamne pas.
- **Les docstrings de test gardent leur statut à part.** Un test énonce son oracle : ce qu'il
  prouve, et ce qu'il ne prouve pas. C'est une contrainte non déductible (test 1) — et la revue
  d'`E16US009` a montré le coût inverse, une docstring qui promettait deux couvertures pour une.
- **Le corps de commit reste long.** C'est le lieu du *pourquoi* daté, versionné, jamais recopié :
  il ne diverge pas, puisqu'il est immuable.
- **Une mention d'origine courte n'est pas de la narration.** « (correctif de revue, E16US004) »
  accolé à un avertissement le **crédibilise** — il dit que le piège s'est déjà refermé sur
  quelqu'un, ce qu'un lecteur pressé a besoin de savoir pour ne pas « simplifier ». Ce qui sort,
  c'est le **récit** : qui l'a trouvé, à quelle passe, ce que disait la rédaction précédente. La
  frontière tient en une question — *est-ce que ça change ce que le lecteur va faire ?*

## Ce qui a été écarté

- **Un seuil mécanique** (« pas plus de N % de commentaire », vérifié en CI). Rejeté : il pousse à
  supprimer l'avertissement utile pour tenir un ratio, et il compte des lignes au lieu de les lire.
  Le pourcentage reste un **indicateur de tri**, jamais une porte.
- **Supprimer tout commentaire hors JSDoc d'API publique.** Rejeté : c'est la version forte de la
  maxime, et elle jette le tiers qui est faux — les couplages invisibles disparaîtraient sans que
  personne ne s'en aperçoive avant le premier bug.
- **Un big bang sur les 151 fichiers.** Écarté à la rédaction (26/08/2026) au titre de la maille
  INVEST (`CLAUDE.md` § Workflow) : un diff de cette taille est irrelisable. ⚠️ **Repris le
  27/08/2026 sur arbitrage du commanditaire** (« tout, maintenant, en une fois »), et ce qui a
  changé l'arbitrage est le **plafond mécanique** ajouté le même jour : un tri sémantique fichier
  par fichier n'est pas relisable en masse, un plafond de huit lignes se **compte**. Voir
  « Application ».
- **Un nettoyage par expression régulière.** Rejeté **sur preuve**, et c'est le point de méthode le
  plus utile de cet ADR. Un motif normalisant « (correctif de 2ᵉ passe, axe C1) » en « (correctif de
  revue) » a été écrit, puis simulé sur les 137 fichiers concernés : il produisait des parenthèses
  jamais refermées (la mention traversait un saut de ligne), des fragments orphelins (`(revue/C1/D)`)
  et des phrases agrammaticales. Un premier jet fusionnait même deux lignes de commentaire, faute
  d'avoir borné `\s*` à la ligne. **Ce nettoyage n'est pas mécanisable : c'est de la prose, elle se
  lit.** D'où le traitement par lots, à la lecture — et non un script.

## Conséquences

**Positives**

- Moins d'assertions non vérifiées : chaque phrase retirée est une divergence future en moins.
- Le raisonnement gagne un domicile **unique** — donc corrigible en un seul endroit.
- Le diff d'une US rétrécit : `E16US009` touchait 45 fichiers, dont une part de prose recopiée.

**Coûteuses / à surveiller**

- ⚠️ **Un renvoi peut mourir.** « cf. ADR-0098 » ne vaut que si l'ADR existe et dit bien cela.
  L'atlas contrôle déjà l'inverse (les fichiers nommés *par* un ADR) ; il ne contrôle pas les ADR
  nommés *par* le code. C'est une limite connue, non fermée par cet ADR.
- Le nettoyage a été **intégral sur le code de production et sur tout `frontend/src`** (E00US027,
  27-28/08/2026) ; `backend/tests/` (395 blocs) et `migrations/` (56) restent au style antérieur,
  et c'est `DETTE-088`. La règle vaut pour tout code neuf, et le plafond la tient mécaniquement.

### Application : un lot démonstratif, puis le dépôt entier

`E00US027` a commencé par un **lot démonstratif de cinq fichiers**, choisis sur un critère objectif
— ≥ 100 lignes de commentaire **et** ≥ 50 % du fichier —, puis a été **élargie au dépôt entier** sur
arbitrage du commanditaire du 27/08/2026, une fois le plafond de huit lignes rendu mécanique.

Mesure de sortie, **recomptée au détecteur livré** : **1 086 blocs backend** (218 fichiers, sur le
périmètre élargi en revue à `atlas/`, `release/` et aux points d'entrée) et **453 blocs front**
(236 fichiers) ramenés sous le plafond, **aucune ligne exécutable modifiée** — vérifié jeton à
jeton. Le cliquet backend est vidé ; le front n'en a pas eu besoin.

**Ensuite, la règle vit au fil de l'eau** : toute US qui touche un fichier le garde sous le plafond,
et `/revue-us` peut relever un commentaire neuf qui ne passe aucun des trois tests — en **mineur**,
jamais en majeur : c'est de la forme, pas un défaut de produit.

## Porté dans le code par

⚠️ Section écrite en **vérifiant dans le code du jour**, pas en déduisant de la décision.

| Décision | Module qui l'applique | Vérifié |
|---|---|---|
| La règle des trois tests, énoncée là où on la lit | [`CLAUDE.md`](../../CLAUDE.md) § « Règles non négociables », règle 13 | oui |
| Lot démonstratif — contrainte invisible **conservée**, narration **retirée** | `frontend/src/shared/ui/pagination.ts` · `frontend/src/features/competition/TableClassement.tsx` | oui |
| Lot démonstratif — archéologie retirée, avertissement d'exhaustivité conservé | `frontend/src/shared/phases/catalogue.ts` | oui |
| Lot démonstratif | `frontend/src/shared/phases/relance.ts` · `frontend/src/features/completude/Completude.tsx` | oui |
| Le raisonnement déplacé, jamais détruit | `docs/adr/0098-un-ecran-projete-pagine-au-lieu-de-defiler.md` (le pourquoi du ratio et du plafond y était **déjà**, ce qui a permis de couper dans `TableClassement.tsx`) | oui — vérifié avant chaque coupe |
| **(i) huit lignes au plus par bloc**, côté backend | `backend/tests/test_commentaires_bornes.py` (+ le fichier de cliquet backend/tests/commentaires_cliquet.txt, **vidé** et gardé vide par `test_le_cliquet_est_vide`) | oui — la suite rougit au 9ᵉ sur tout le code de production ; `tests/` et `migrations/` restent hors porte (`DETTE-088`) |
| **(i) huit lignes au plus par bloc**, côté front | `frontend/src/commentaires.test.ts` (pendant vitest, **sans cliquet** — le front a été *ramené* sous le plafond par E00US027, 453 blocs, il n'y avait donc pas de baseline à garder) | oui — `npm test` rougit au 9ᵉ, JSX et CSS compris depuis la revue |
| Le comportement est **inchangé** : c'est un nettoyage de prose | la porte mécanique complète (`pytest`, `npm test`, `tsc`, `ruff`, `mypy`) | oui — aucune ligne exécutable modifiée. ⚠️ Borne : les docstrings de handlers FastAPI alimentent l'attribut `description` d'`/openapi.json`, qui change ; aucun contrat n'en dépend aujourd'hui (E00US025 non livrée) |
