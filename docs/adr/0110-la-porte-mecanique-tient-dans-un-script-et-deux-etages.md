# ADR-0110 — La porte mécanique tient dans un script, et en deux étages

- **Statut** : Accepté
- **Date** : 2026-09-19
- **US** : `E00US031`
- **Décideurs** : Commanditaire / Architecte
- **S'appuie sur** :
  - [ADR-0086](0086-un-atlas-genere-le-depot-cartographie-sans-dependance.md) — l'atlas en stdlib
    pure, et son job CI **sans `pip install`** qui le prouve par construction. `porte.py` reprend
    son découpage en trois groupes plutôt que d'en inventer un autre
  - [ADR-0102](0102-la-documentation-porte-des-pointeurs-pas-des-copies.md) — « un fait, un lieu » :
    c'est lui qui interdit de recopier `ci.yml` dans un script local, et qui impose le garde-fou
    de correspondance décrit plus bas

## Contexte

L'US est partie d'un constat de l'utilisateur — « la porte met parfois 40 minutes » — et d'une
hypothèse de l'assistant : l'essentiel de ce temps serait de l'**orchestration** (un tour de modèle
entre chacune des douze commandes, avec ingestion de sorties de tests volumineuses), et non du
calcul. **Les mesures ont démenti cette hypothèse.** Elles sont consignées ici parce que ce
démenti, plus que la décision, est ce qui empêchera de refaire le même raisonnement.

**1. Le calcul, mesuré commande par commande** (poste Windows, **4 cœurs logiques**, 16 Go) :
`pytest` 444,8 s · `npm test` (vitest) 224,5 s · `pip-audit` 49,4 s · `npm run lint` 35,4 s ·
`build` 16,6 s · `typecheck` 14,6 s · `npm ci` 16,0 s · `prettier` 9,2 s · atlas 5,7 s ·
`npm audit` 2,7 s · `mypy --strict` (cache chaud) 1,8 s · `ruff` 0,24 s. **Total : 821 s, soit
13 min 41.**

**2. L'orchestration ne coûte presque rien.** Le registre
[`metriques-revue.md`](../metriques-revue.md) enregistre déjà la durée de porte sur **52 passes** :
la médiane est de **11 à 13 minutes**, cohérente avec le calcul pur. Une **seule** passe atteint
40 minutes, et le registre en donne la cause en toutes lettres : elle était *« lancée **en
parallèle** de la revue »*. Sur 4 cœurs, la porte et les cinq agents de revue se disputaient la
machine. L'agent `porte-mecanique` tourne par ailleurs sur `model: haiku` — ses tours sont rapides,
ils ne pouvaient pas représenter vingt-six minutes.

**3. Deux suspects innocentés.** Le montage de base de données n'est pas le goulot :
`tests/base_migree.py` joue les 55 migrations **une fois par session** puis copie le fichier
(2,98 s au premier appel, **1,9 ms** par copie) ; un montage d'app complet coûte 11,7 ms, soit 3 %
de `pytest`. Et il n'existe **aucune attente réelle** : zéro `sleep` backend, zéro `setTimeout`
front, Zeroconf mocké, WebSocket en process. Le temps de `pytest` est **diffus** dans 776 tests
d'API à 0,34 s pièce, dont 246,8 s en phase `call` : il n'y a pas de test coupable, il y a un
volume.

**4. Sélectionner par chemin coûte plus cher que tout collecter.** 67 fichiers passés en arguments
demandent **13,2 s** de collecte, là où le répertoire entier (249 fichiers) n'en demande que
**7,5 s** : chaque argument déclenche sa propre résolution de rootdir et de `conftest`, et sur
Windows la rafale de `stat` coûte plus que le parcours d'arbre unique.

**5. Ce qui reste, et qui n'existait pas.** La répartition par famille désigne un étage rapide sans
ambiguïté : **domaine + service = 2719 tests (63 % de la suite) pour 3,1 s attribués** — l'oracle 120 s'y
ajoute pour ~4 s, quand
API + migrations pèsent **358 s (81 % du temps) pour 19 % des tests**. L'isolation du domaine
(règle 1) — décidée pour la propreté — produit gratuitement un étage de vérification court. **Il
n'était simplement pas outillé.**

## Décision

**1. Les vérifications vivent dans un script, `backend/porte.py`.** Il enchaîne tout sans
intervention, écrit chaque sortie dans `.porte/<pid>/<nom>.txt` (ignoré de git ; un sous-dossier par
processus, ce dépôt faisant tourner des agents concurrents dans le même arbre) et n'affiche qu'un tableau
`vérification → état → durée`. Le détail ne se lit **que** pour les lignes rouges. Le gain n'est pas
sur l'horloge : c'est que l'agent de porte n'ingère plus des milliers de lignes de sortie, et que
**l'utilisateur peut lancer la porte lui-même**, sans agent.

**2. Deux étages.** `--rapide` tourne pendant l'implémentation ; l'étage complet reproduit la CI et
se lance **une fois**, avant la revue.

**3. Parallèle à l'étage rapide, séquentiel à l'étage complet.** Mesuré à conditions égales :

| Étage | Séquentiel | Parallèle |
|---|---:|---:|
| Rapide | 68,4 s | **46,3 s** |
| Complet | **845 s** | 905 s |

⚠️ **Le parallélisme est contre-productif à l'étage complet, et c'est contre-intuitif.** `pytest` y
domine et **double** sous contention — 479,6 s en séquentiel contre 899,6 s en parallèle — si bien
que le recouvrement ne compense jamais. À l'étage rapide au contraire, les tâches sont courtes et de
durées comparables, et le recouvrement gagne un tiers. **Ne pas uniformiser les deux étages** : le
défaut de chacun est mesuré, pas choisi par symétrie.

**4. La sélection des tests passe par des marqueurs, jamais par une liste de chemins** (mesure 4).
Huit familles — `domaine`, `service`, `api`, `repository`, `migration`, `atlas`, `oracle`,
`divers` — sont posées **automatiquement à la collecte** par `tests/conftest.py`, d'après le nom du
module : les 249 fichiers de test vivent à plat, le chemin ne discrimine rien. `--strict-markers`
est activé : il fait échouer un marqueur **posé** sans être déclaré. ⚠️ Il ne valide **pas**
l'expression `-m` — mesuré : `pytest -m domaien` rend `no tests collected` sans broncher. Ce qui
protège d'une expression vide est le **code de sortie 5** de pytest, que `porte.py` lit comme
rouge ; et ce qui protège d'une famille inexistante dans une expression **valide** est
`test_l_etage_rapide_ne_selectionne_que_des_familles_existantes`.

**5. `ci.yml` reste la référence, et un test garde la correspondance.** `porte.py` cite pour chaque
vérification la ligne `run:` correspondante ; `tests/test_porte_couvre_la_ci.py` compare les deux
listes **dans les deux sens**. Une vérification ajoutée à la CI sans l'être à la porte fait rougir
un test. Sans lui, la porte locale passerait au vert sur un dépôt que la CI refuse.

**6. Le vérificateur de `requirements.txt` sort de `ci.yml`.** Ces 40 lignes vivaient en
`shell: python` inline ; les deux portes en auraient gardé chacune une copie. Elles deviennent
`backend/verifier_requirements.py`, que la CI **et** la porte appellent.

**7. `npm ci` reste systématique.** Le rendre conditionnel au lockfile avait été envisagé, puis
**abandonné sur mesure** : il coûte **16 secondes**, et c'est la seule étape qui confronte
`node_modules` au lockfile — la garde contre le piège `@emnapi`. Seize secondes ne s'échangent pas
contre un trou dans une vérification.

**8. `jsdom` n'est instancié que pour les tests qui en ont besoin.** `vitest` le montait pour les
134 fichiers de test du front, alors que `environment` cumulait **423,8 s** de temps worker contre
66 s de tests réels. Deux projets Vitest, répartis par une convention que le dépôt suivait déjà sans
le savoir : `.test.tsx` → composant → `jsdom` (60 fichiers, **tous** important Testing Library) ;
`.test.ts` → logique pure → `node`. Mesuré à suite complète : **224,5 s → 150 s**.

⚠️ Les exceptions sont une **table justifiée**, pas une liste. La détection automatique ne voit que
les usages **directs** du DOM ; un besoin **transitif** — un test qui n'écrit ni `document` ni
`localStorage` mais exerce un chemin qui en dépend — ne se détecte pas et s'inscrit à la main avec
sa raison. Trois modules étaient dans ce cas et exerçaient sous `node` des chemins morts
(`appliquerTheme` sort tôt sans `document`, un store `persist` devient inopérant sans
`localStorage`) : ils restaient **verts en couvrant moins**.

**9. Du CPU et des tokens contre du temps humain, jamais l'inverse.** L'arbitrage du 19/09/2026 qui
a commandé cette US : une passe qui consomme plus vaut mieux que cinq qui consomment moins, mais
**jamais** en dégradant une vérification. Conséquences opérationnelles : on parallélise **quand
c'est mesuré gagnant** (décision 3), on lance les portes en arrière-plan, on ne cible pas la porte
après correctifs. La règle vit dans `CLAUDE.md`
(`<!--regle:cpu-et-tokens-contre-temps-humain-->`) et son artefact d'application est
[`docs/checklist-implementation.md`](../checklist-implementation.md), tirée du dépouillement des
152 corps de commit de correction de revue. ⚠️ **Cette checklist est un fichier à lire, pas un
mécanisme** : rien ne la vérifie, et c'est sa limite — dite en tête du fichier.

## Conséquences

**Ce qu'on gagne, honnêtement.** L'étage complet ne devient **pas** plus rapide : 845 s mesurés
contre une médiane historique de 11 à 13 minutes — c'est un statu quo. Ce qui change est ailleurs :

1. **Un étage rapide de ~30 s** sur 2738 tests, `ruff`, `mypy --strict`, l'atlas et le typage
   TypeScript. Il n'existait pas. C'est le seul vrai gain, et il porte sur la **fréquence** de
   vérification, pas sur sa durée.
2. **La porte ne se lance plus pendant la revue.** C'est la cause mesurée de la seule passe à
   40 minutes, et aucune optimisation de `pytest` n'y aurait changé quoi que ce soit.
3. **La correspondance avec la CI devient vérifiée** au lieu d'être supposée.
4. **L'utilisateur peut lancer la porte seul**, sans agent ni session, et **sans activer le
   venv** : `porte.py` cherche le sien à côté de lui, faute de quoi la commande prescrite
   (`python backend/porte.py`) tomberait sur l'interpréteur système et rendrait un tableau tout
   rouge qu'on prendrait pour une régression.

⚠️ **Ce que l'étage rapide ne couvre pas**, et c'est le risque principal : les **776 tests d'API**,
les migrations, les repositories, `eslint`, `prettier`, `vitest`, le `build`, les deux audits
et les **cliquets documentaires** de `test_atlas_corpus` (famille `atlas`, 43,8 s mesurées : elle
doublerait l'étage). Il
valide la **règle métier**, jamais l'intégration. Une US qui touche un endpoint, une migration ou le
rendu front n'est **pas** vérifiée par lui, et il ne remplace jamais l'étage complet avant la PR.

⚠️ **Un module de test hors convention de nommage tombe en `divers` sans rien signaler**, et sort
de fait de l'étage rapide. `tests/test_familles_de_tests.py` gèle la liste des 35 modules
actuellement hors convention : un module neuf y fait échouer un test.

**Ce qui reste ouvert.** La collecte pytest coûte **7,5 s** à chaque invocation, soit 16 % de
l'étage rapide — inscrite en [`DETTE-105`](../dette.md#dette-105--la-collecte-pytest-coûte-75-s-à-chaque-invocation).

**Ce qui a été écarté.** `pytest-xdist` : la mesure 3 montre que `pytest` souffre déjà de la
contention sur 4 cœurs ; lui en donner davantage aggraverait ce qu'on vient de constater. Il
ajouterait une dépendance (règle 11) et un risque d'intermittence sur un SQLite single-writer
(règle 7) pour un gain que le matériel interdit. **Le matériel a tranché, pas une préférence.**

**Enseignement de méthode.** L'hypothèse de départ — « 26 minutes d'orchestration » — venait d'une
**soustraction entre un calcul mesuré et un pic rapporté**, sans vérifier que le pic était
représentatif. Le registre contenait déjà la réponse. ⚠️ Avant d'optimiser sur un écart, vérifier
**les deux termes** de la soustraction, et chercher si le dépôt ne mesure pas déjà la grandeur en
question.

## Porté dans le code par

- `backend/porte.py` — les deux étages, le défaut parallèle/séquentiel par étage, le tableau de
  synthèse, et le champ `ligne_ci` qui rattache chaque vérification à la CI
- `backend/tests/conftest.py` — `FAMILLES_DE_TESTS`, `famille_du_module` et le hook
  `pytest_collection_modifyitems` qui pose les marqueurs à la collecte
- `backend/pyproject.toml` — `[tool.pytest.ini_options]` : les huit marqueurs déclarés et
  `--strict-markers`
- `backend/tests/test_porte_couvre_la_ci.py` — la correspondance `porte.py` ↔ `ci.yml` dans les deux
  sens, et un test qui vérifie que le parseur de `ci.yml` n'est pas cassé
- `backend/tests/test_familles_de_tests.py` — le gel des modules hors convention, et l'absence de
  chevauchement entre familles
- `backend/verifier_requirements.py` — le contrôle extrait de `ci.yml`, appelé par les deux portes
- `.github/workflows/ci.yml` — appelle désormais `verifier_requirements.py` au lieu de sa copie
- `.claude/agents/porte-mecanique.md` — l'organe de la décision 1 : il lance une commande et lit
  les seuls journaux rouges, au lieu d'ingérer la sortie de douze
- `.claude/commands/revue-us.md` § étape 0 — les trois contrôles qui restent à l'œil (mode, compte
  attendu, présence de `pytest` et `vitest`), les seuls que la porte ne peut pas faire d'elle-même
- `frontend/vite.config.ts` — les deux projets Vitest de la décision 8
- `frontend/src/test-environnement.ts` — la table justifiée des exceptions et la détection des
  usages directs
- `frontend/src/test-environnement.test.ts` — vérifie les deux sens, plus qu'aucun fichier de test
  n'échappe aux deux projets
- `CLAUDE.md` § Commandes — les deux étages, et la règle « jamais pendant la revue »
