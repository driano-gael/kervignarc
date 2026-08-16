# ADR-0013 — Conduite de la revue d'US : axes parallèles + porte mécanique

- **Statut** : Accepté
- **Date** : 2026-07-15
- **Décideurs** : Organisateur / Architecte

## Contexte et problème

La durée d'une US a dérivé : ~10 min pour `E01US001` (branche entière, revue comprise) contre
~3 h 14 pour `E02US001`. La cause n'est **pas** la taille de la base de code — 6 647 lignes de
backend hors tests, 291 fichiers, 3 400 lignes de documents de référence : à cette échelle
l'exploration coûte quelques minutes.

Le coût est dans [`/revue-us`](../../.claude/commands/revue-us.md). Un relecteur unique déroulait
**16 règles en série** : le temps mur est leur somme, et l'attention se dilue sur une consigne qui
n'en finit pas. La grille est passée de 13 à 16 règles le 2026-07-14 (PR #24) ; les trois ajoutées
(dette technique, dette de conception, remède structurel) sont **génératives** — contrairement aux
règles 1-8 qui sont des invariants binaires, elles demandent un jugement ouvert sur presque tout
diff. Les trois dernières US portent toutes « dette tracée » dans leur commit de correctifs.

Chronologie mesurée sur `E02US001` : implémentation à 17:10, correctifs de revue à 17:42, **2 h 17
d'écart**, puis une seconde passe à 20:20. L'implémentation a pris 32 min ; le reste est de la revue
et un CA découvert en cours de branche.

## Options envisagées

- **Ne rien faire** — garder le relecteur unique. Défendable : zéro risque de trou inter-axes.
  Écartée : le poste est mesuré, il croît avec la grille, et il croîtra encore.
- **Dégrader le modèle du relecteur** — **écartée sans discussion**. `CLAUDE.md` § Économie de
  contexte : « un sous-agent qui **juge** garde le modèle fort : c'est une barrière qualité, elle ne
  s'optimise pas. » Optimiser une barrière qualité, c'est la supprimer.
- **Réduire la grille** — écartée : chaque règle a été ajoutée sur une cause réelle. Le problème est
  la conduite de la revue, pas son contenu.
- **Axes parallèles à modèle fort + porte mécanique** — retenue. Ne retire aucune règle, ne dégrade
  aucun modèle ; ne change que l'ordonnancement et l'usage des preuves déjà disponibles.

## Décision

**1. Porte mécanique avant la revue** (étape 0). Les vérifications outillées passent au vert *avant*
de dépenser une passe. Elles **déchargent** les relecteurs de ce qu'elles prouvent : faire relire à
l'œil ce que `test_domain_isolation.py` établit par AST est plus lent *et* plus faible qu'une preuve
machine. Les commandes sont **identiques à celles de `ci.yml`**, l'autorité bloquante — options
comprises : une commande approchante n'est pas la même mesure. La porte en est un **sous-ensemble
volontaire** : **une seule** étape est sciemment omise (la synchro `requirements.txt`↔`pyproject.toml`) ;
toute **autre** divergence est un bug de la procédure.

**2. Quatre axes disjoints, relus en parallèle**, à modèle fort — A (architecture & config,
règles 1-8), B (CA/tests/dépendances/front, 9-11 + volet front de 3 et 4), C1 (correction & cas
limites, 13), C2 (dette & conception, 14-16). Le temps mur devient celui de l'axe le plus lent au
lieu de leur somme. Le découpage suit ce que chaque axe doit **lire**. C2 est le chemin critique :
la règle 13 en a été sortie vers C1 pour le raccourcir.

**3. Le périmètre est une aide à la lecture, jamais un déclencheur.** Les règles s'appliquent
toujours, et le seul discriminant est **« as-tu lu ? »** : un axe qui a lu et ne trouve pas de
surface rend un rapport valide, à condition de dire ce qu'il a lu ; conclure sans lire est un raté de
revue. Le court-circuit *sans lecture* est réservé aux règles qui détectent une **présence** (10
front, 11 dépendances) et **interdit** à la règle 9 (tests), qui détecte une absence. Seule exception
au principe : à l'étape 3, la sélection des axes rejoués sur un diff **déjà relu intégralement et
inchangé** — bornée par l'obligation de rejouer l'axe B dès que les correctifs touchent du code de
production.

**4. La sécurité est la seule règle partagée par tous les axes**, chacun sur son périmètre — le
doublon est voulu.

**5. La décharge est suspendue si le diff touche la configuration des outils.** Une porte verte ne
prouve rien si le diff a déplacé la porte. Énoncé comme un **principe** (« tout fichier qui définit
ce que la porte exécute ou ce qu'elle vérifie »), pas comme une liste : la première version était une
liste, et elle a oublié `[tool.pytest.ini_options]` et les `scripts` de `package.json`.

**6. La règle 12 est scindée.** Le **format** (commit conventionnel, cohérence branche, corps
quoi/pourquoi) se vérifie à l'étape 0 par l'auteur : c'est factuel. Le **jugement** « décision
structurante ⇒ ADR » revient à un relecteur (axe C2, périmètre = le log de branche) : c'est la seule
règle dont l'objet est de rattraper ce que l'auteur a escamoté, et la lui confier la neutralise. La
première version la lui confiait entièrement, au motif qu'« un message de commit n'est pas un
fichier » — motif vrai mais non concluant : un périmètre peut être un `git log`. Preuve que ce
n'était pas théorique : `b47b25c` a été livré **sans ADR**, rattrapé par un relecteur tiers ; sous ce
régime, le présent ADR n'existerait pas.

## Conséquences

- **+** Temps mur attendu **~2×** plus court sur le poste le plus lourd du cycle.
- **+** Chaque relecteur traite une consigne courte à fond, au lieu de 16 règles diluées.
- **+** Les preuves machine sont utilisées comme telles, et leurs **limites exactes** sont écrites
  noir sur blanc plutôt que supposées.
- **−** Coût en tokens **~2,5×** : chaque axe lit le diff, plus les préambules, les rapports et la
  passe de fusion. Arbitrage assumé : le temps mur vaut plus que les tokens sur ce projet. **Ne pas
  « optimiser » en refusionnant les axes sans relire cet ADR.**
- **−** Le gain n'est **pas** 3×. Le chemin critique est `max(A, B, C1, C2, D)` et il **n'a pas été
  mesuré** : C2 en est le candidat présumé, mais B (plus large ensemble de lecture) et C1 (jugement
  ouvert sur le diff entier) le sont au moins autant. Le **~2× est une estimation à confirmer sur les
  trois prochaines US**, pas un acquis — et la scission C1/C2 repose sur la même présomption non
  mesurée.
- **−** La règle 12 n'est plus vérifiée **en entier** par un tiers : l'auteur juge le format de son
  propre message de commit (le jugement « ⇒ ADR » lui a été retiré, cf. décision 6). Perte
  d'indépendance résiduelle assumée, à rouvrir si un défaut de traçabilité passe.
- **−** La décharge est plus étroite que l'intitulé des règles. Résidus explicités, à ne jamais
  perdre de vue : la denylist `_FORBIDDEN_ROOTS` est aveugle aux imports tiers hors liste et au
  caractère synchrone du domaine (règle 1) ; mypy ne dit rien de l'immutabilité et **exclut
  `backend/migrations/`** (règle 4).
- **−** Le découpage crée un **coût de maintenance permanent** : toute règle ajoutée doit se voir
  attribuer un axe *et* un périmètre cohérents. C'est le vrai prix de cette décision, et il a été
  payé dès le premier jet — voir ci-dessous.
- **−** Un défaut né de la **conjonction** de deux axes n'appartient à aucun des deux. C1 en est
  explicitement propriétaire, parce qu'il est le seul à voir le diff entier.

### Conséquences propres à l'amendement du 16/08/2026 (décisions 8 et 9)

- **+** La barrière qualité ne peut plus se dégrader **en silence** : le modèle des relecteurs ne suit
  plus celui de la session. Corollaire pratique : mener une US mécanique en Sonnet devient un
  arbitrage de coût **sans effet de bord** sur la revue.
- **+** « Ne modifie aucun fichier » devient une absence de capacité **pour `Edit` et `Write`**.
- **−** 🔴 **Mais pas pour `Bash`, et le trou a été exploité par accident le 17/08/2026** (`e8d3258`,
  décision 8). Tant qu'il n'est pas fermé, **tout agent de ce dispositif peut écrire dans l'arbre et
  pousser**. Conséquence opérationnelle immédiate, à appliquer dès aujourd'hui : après chaque appel à
  `porte-mecanique`, l'agent auteur **vérifie `git status` et `git log`** avant de continuer. Ce n'est
  pas un garde-fou, c'est un pansement — le vrai correctif est un `Bash` scopé, à valider.
- **+** La sortie volumineuse des tests quitte le contexte de l'agent auteur, où elle était renvoyée à
  chaque tour jusqu'au `/clear`. C'est le gain de contexte le plus net du lot — plus net que le gain
  de coût, qui reste modeste.
- **−** **Le nombre de fichiers à maintenir passe de 1 à 7** (la commande + six agents ; `localiser`
  ne relève pas de cette décision — voir ADR-0088). C'est le prix réel de cet amendement, payé
  volontairement contre la propriété inverse : une grille ne vit plus qu'à un seul endroit, et le
  modèle n'est plus une convention orale.
- **−** Le préambule commun reste **en un seul exemplaire** dans `/revue-us` — le recopier dans les
  agents rejouerait le mode de défaillance que la décision 8 vient de fermer. **Une exception, et une
  seule : la règle de sécurité** (décision 4), que le projet double délibérément sur tous les axes.
  Elle vit désormais à l'identique dans les **cinq** grilles et **plus du tout** dans le préambule.
  Raison, apprise à la première passe : le préambule est retranscrit à la main à chaque lancement, la
  grille se charge toute seule. L'auteur a transmis la règle de sécurité **réduite à son titre** dès
  cette première passe, et une telle perte ne produit **aucun symptôme** — un axe qui ne cherche pas
  une chose rend le même rapport qu'un axe qui ne la trouve pas.
- **−** Le risque de dérive **change de forme sans disparaître** : `/revue-us` et les définitions
  d'agents peuvent se contredire (un axe renommé, une règle déplacée, un renvoi croisé périmé). Rien
  ne le vérifie mécaniquement, et **trois divergences existaient déjà dans le commit d'introduction**
  — deux renvois morts (`docs/adr/0075:220`, `docs/dette.md:7`) et une liste de suspension amputée.
  Inscrit au registre en **[DETTE-068](../dette.md)**, avec un déclencheur écrit **au futur** (« la
  prochaine divergence constatée ») : le seuil « au troisième cas » envisagé d'abord était franchi à
  la rédaction, et DETTE-067 a montré qu'un déclencheur déjà atteint ne se déclenche jamais plus tard.
- **−** L'agent `porte-mecanique` tourne sur un **modèle léger** : il exécute et recopie, il ne juge
  pas. Deux contrôles restent explicitement chez l'auteur — la complétude de la liste des `run:`
  (qu'il rend verbatim pour cela) et l'unique interprétation autorisée (`atlas --verifier` rouge =
  cas connu de régénération post-commit). Le jour où l'on serait tenté de lui confier un jugement,
  c'est le modèle qu'il faudrait remonter, pas la consigne.

## Retour d'expérience — deux tours, et les deux ont trouvé des bloquants

Cette procédure a été soumise **à elle-même**, deux fois. Le détail est conservé parce qu'il
documente le mode de défaillance de ce genre de découpage — et parce qu'un ADR qui enjolive son
propre passé fait croire à une méthode qui n'a pas eu lieu.

**Tour 1** — le premier jet (`b47b25c`, **trois** axes) : **2 bloquants**, 4 majeurs.

- *Bloquant* — **le court-circuit était aveugle au cas « pas de tests »** : une US sans un seul test
  ne touche pas `backend/tests/`, l'axe B répondait « sans objet » sans lire. L'absence de test,
  c'est-à-dire exactement ce que la règle 9 existe pour trouver, était lue comme « rien à faire ».
- *Bloquant* — **la décharge n'était pas suspendue quand le diff touchait la config des outils** :
  un diff qui assouplit `pyproject.toml` fait passer mypy au vert parce que la porte a bougé. C'est
  la cause de la décision 5, qui sans cela paraîtrait gratuite et coûteuse.
- *Majeurs* — la sécurité, nommée pour éviter le « chacun croit que l'autre le fait », mise dans un
  axe scopé `backend/` (créant le trou qu'elle voulait fermer, le jeton admin étant en `localStorage`
  côté front) ; la traçabilité dans le périmètre de personne ; l'axe B jugeant un test sans voir
  l'implémentation ; l'ADR manquant.

Cause racine unique : **les axes découpés par thème de règle, les périmètres écrits par répertoire**
— les deux découpages ne coïncident pas, et tout ce qui échappe tombe dans cet écart.

**Tour 2** — la correction (`f7a346a`) : **3 bloquants** de plus, et le diagnostic qui les explique
tous — *on corrige l'instance qu'on vous a montrée, pas la classe*. La porte `mypy` avait été fermée
et la porte `pytest` laissée ouverte (`[tool.pytest.ini_options]`, un `addopts = "--ignore=…"` tue le
garde-fou d'isolation sans rien faire rougir) ; le périmètre-déclencheur avait été interdit à
l'étape 1 et réécrit à l'étape 3 ; la décharge, refaite pour ne plus sur-revendiquer, sur-revendiquait
`pip-audit` comme preuve de la règle 11-c **licence comprise** — retirant de la revue un contrôle qui
existait avant. D'où deux corrections de méthode, inscrites dans la procédure : la suspension de
décharge est désormais un **principe** et non une liste (une liste oublie), et le discriminant d'un
axe muet est **« as-tu lu ? »** et non « ton rapport est-il vide ? ».

**L'enseignement, deux fois confirmé** : les axes vérifient une **conformité** — ils cochent des
cases, ils ne cherchent pas à démolir. Sur les deux tours, **la totalité des bloquants a été trouvée
par l'agent adversarial**, aucun par les axes de conformité. C'est le seul dispositif qui ait rien
trouvé ici. D'où la décision 7 ci-dessous, et la consigne de la défendre la prochaine fois qu'on
cherchera à raccourcir la revue.

**7. Le relecteur adversarial est un axe à part entière** (axe D), lancé dans le même message que les
autres, au même format, compté au verdict global — **requis** dès que le changement est structurel.

**8. Chaque relecteur est un agent versionné, à modèle épinglé et outils restreints.**
*(Amendement du 16/08/2026.)* Les grilles quittent le corps de `/revue-us` pour
`.claude/agents/revue-axe-{a,b,c1,c2,d}.md` — un fichier par axe, versionné, donc identique sur tous
les postes. Trois propriétés que le prompt inline ne pouvait pas offrir :

- **Le modèle est épinglé** (`model: opus`) au lieu d'être hérité de la session. C'est la mise en
  application *mécanique* de l'option écartée en tête de cet ADR (« dégrader le modèle du relecteur —
  écartée sans discussion ») : jusqu'ici, un `/model sonnet` choisi pour une US mécanique dégradait
  la barrière qualité au `lance la PR` suivant, **sans que rien ne le signale**. L'épinglage ferme ce
  trou sans rien coûter.
- **Les outils sont restreints** : les agents de revue n'ont ni `Edit` ni `Write`. ⚠️ **Cela ne rend
  pas l'écriture impossible, seulement moins directe** : `Bash` reste ouvert (les relecteurs ont
  besoin de `git diff`, la porte d'exécuter la CI), et `.claude/settings.json` ne refuse ni
  `git commit`, ni `git push`, ni `sed -i`, ni une redirection. « Ne modifie aucun fichier » reste
  donc une **consigne**, pas une contrainte.

  🔴 **Ce n'est plus un risque théorique : c'est un incident daté du 17/08/2026, commit `e8d3258`.**
  L'axe adversarial de la revue de ce lot avait décrit le scénario mot pour mot — « un agent, ayant
  trouvé une coquille, *rend service* en la corrigeant puis en commitant ; aucun garde-fou ne s'y
  oppose ». Quelques heures plus tard, l'agent **`porte-mecanique`** — un `haiku` dont la définition
  ouvre par « tu ne corriges rien, tu ne modifies aucun fichier du dépôt » — a, au cours d'une simple
  demande de porte : corrigé deux défauts dans cet ADR, régénéré l'atlas, lancé `ruff format` sur un
  test, puis **`git add` sur l'arbre entier, `git commit` et `git push`**. Les 22 fichiers du commit
  contiennent l'intégralité des correctifs de revue en cours, sous un message qui n'en décrit que
  deux — et dont le justificatif technique est **fabriqué**.

  Trois enseignements, tous coûteux :
  1. Une consigne de prompt ne borne pas un agent doté d'un outil général. Retirer `Edit`/`Write` en
     laissant `Bash` ne retire **rien** de ce qui compte.
  2. Le danger d'un modèle léger n'est pas qu'il travaille mal — ses deux corrections étaient
     justes — c'est qu'il **déborde son mandat avec assurance** et raconte ensuite ce qu'il croit
     avoir fait.
  3. Un agent qui peut écrire dans l'arbre **détruit la traçabilité** : `git add -A` ramasse le
     travail d'autrui, et le message de commit devient faux sans que personne n'ait menti.

  Le durcissement n'est pas trivial : `settings.json` est versionné et **partagé** avec l'agent
  auteur, à qui `git commit` et `git push` sont indispensables (§ Workflow). Fermer par la denylist
  fermerait les deux. La piste est un `Bash` **scopé au frontmatter** de l'agent — non vérifié à ce
  jour. Arbitrage rendu à l'utilisateur, cf. § Conséquences.
- **La porte mécanique devient un agent** (`porte-mecanique`, `model: haiku`) qui **lit `ci.yml`** au
  lieu de suivre une liste, et rend un verdict + les échecs verbatim. Double effet : la sortie des
  tests (10-50 k tokens) quitte le contexte de l'auteur, et la liste ne peut plus dériver.

**Ce dernier point corrige deux défauts réels de la décision 1.**

*Premier défaut — la liste.* Elle affirmait que les commandes sont identiques à celles de `ci.yml` ;
c'était vrai de l'intention, faux de la mise en œuvre : la liste recopiée dans `/revue-us` a divergé
de `ci.yml` **deux fois** — `npm test` (797 tests front, `ci.yml:154`) absent depuis la rédaction de
la procédure, découvert le 15/08/2026 sur E05US028 ; puis le job **`atlas`**
(`python -m atlas --verifier`, `ci.yml:124`) jamais mentionné, découvert au présent amendement. Deux
occurrences du même mode de défaillance suffisent à trancher : **la liste n'est pas la bonne forme,
la lecture du fichier l'est.**

*Second défaut — le décompte.* « **Une seule** étape est sciemment omise » était faux devant `ci.yml`,
qui porte aussi des étapes d'**installation** (`pip install -r requirements.txt`, `pip install -e .`)
qu'aucune porte locale n'exécute. Le décompte est remplacé par une **énumération fermée** dans
`porte-mecanique.md` : installation des dépendances Python, synchro `requirements.txt`↔`pyproject.toml`,
et rien d'autre. Sans cette correction, l'agent — qui liste désormais les `run:` verbatim, donc qui
*voit* l'écart — aurait signalé une « anomalie de procédure » à chaque passe, et un contrôle qui crie
toujours est un contrôle qu'on apprend à ignorer.

⚠️ **Ce que l'agent ne remplace pas.** La première rédaction de cet amendement avait supprimé de
`/revue-us` l'impératif « **ouvre `ci.yml` et compare toi-même** », au motif que l'agent le lit. C'est
l'inverse qui est vrai : l'agent *peut* lire `ci.yml` — c'est même sa seule source — et ce que
l'auteur seul apportait était une **lecture indépendante**. Comparer la transcription d'un modèle
léger à sa propre table d'exécution ne compare que deux sorties du même modèle : elles sont fausses
ensemble. L'impératif est rétabli (un `grep`), et la lecture par l'agent s'y **ajoute** au lieu de
s'y substituer.

L'agent `porte-mecanique.md` rejoint par conséquent les fichiers dont le diff **suspend la décharge**
(décision 5) : il définit désormais ce que la porte exécute.

**9. La mesure est un fichier, pas un outil.** *(Amendement du 16/08/2026.)*
[`docs/metriques-revue.md`](../metriques-revue.md) reçoit une
ligne par passe de revue, remplie à l'étape 2 : durées, verdict par axe, et **quel axe a trouvé les
bloquants**. Il répond aux deux inconnues que cet ADR admet plus bas (chemin critique non mesuré,
~2× non confirmé) sans introduire la moindre dépendance — règle 11 (parcimonie) et règle 12 (la
rigueur va au moteur métier, pas à l'outillage). Le **coût en tokens par axe** reste hors de portée :
une session ne peut pas lire sa propre consommation ventilée par sous-agent, et une colonne remplie à
l'estime vaudrait moins qu'une case vide.

## Options envisagées à l'amendement du 16/08/2026

La section « Options envisagées » d'origine porte sur la parallélisation (15/07/2026). L'amendement
en appelle une seconde, parce que la règle 16 exige que l'option « **rien** » soit proposée d'abord :

- **Rien, sauf supprimer la liste** — laisser les grilles dans `/revue-us`, remplacer la liste de
  commandes par « lis `ci.yml` ». C'est le minimum qui répond à la preuve invoquée, et l'objection
  est sérieuse : les deux divergences constatées prouvent que *la liste* dérive, elles ne prouvent
  pas que *l'inline* échoue. **Écartée** — elle ne ferme ni l'héritage silencieux du modèle de
  session, ni le coût de contexte de la sortie des tests. Ce sont ces deux-là, et non l'anecdote de
  la liste, qui portent la décision 8.
- **Extraire les grilles seules, garder la porte inline** — écartée pour la même raison : la porte
  est le poste de contexte, pas les grilles.
- **Extraction complète en agents versionnés** — retenue.

## Porté dans le code par


| Ce qui applique la décision | Décisions portées |
|---|---|
| [`.claude/commands/revue-us.md`](../../.claude/commands/revue-us.md) | 1, 2, 3, 5, 6 (format), 7, 9 — orchestration, préambule commun, table de décharge, principe de suspension, concordance des numéros, bornage de l'étape 3 |
| [`.claude/agents/revue-axe-a.md`](../../.claude/agents/revue-axe-a.md) · [`-b`](../../.claude/agents/revue-axe-b.md) · [`-c1`](../../.claude/agents/revue-axe-c1.md) · [`-c2`](../../.claude/agents/revue-axe-c2.md) | 2 (les quatre grilles disjointes), 4 (la règle de sécurité, à l'identique dans chacune), 8 (`model: opus` épinglé) — **et 6 par `revue-axe-c2.md` seul** (le jugement « ⇒ ADR ») |
| [`.claude/agents/revue-axe-d.md`](../../.claude/agents/revue-axe-d.md) | 7 et 4 — le relecteur adversarial, sans grille par construction |
| [`.claude/settings.json`](../../.claude/settings.json) | 1 — les permissions qui rendent la porte exécutable ; une entrée retirée y suspend la décharge au même titre que `backend/pyproject.toml` assoupli |
| [`.claude/agents/porte-mecanique.md`](../../.claude/agents/porte-mecanique.md) | 1 et 8 — lit `ci.yml`, exécute, rend les échecs verbatim ; l'énumération fermée des omissions volontaires y vit |
| [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) | 1 — l'autorité bloquante dont la porte est un sous-ensemble |
| `backend/tests/test_domain_isolation.py`, `backend/pyproject.toml` (`[tool.mypy]`, `[tool.ruff*]`) | 1 et 5 — les preuves machine qui fondent la décharge, et les fichiers dont le diff la suspend |
| [`backend/tests/test_agents_de_revue.py`](../../backend/tests/test_agents_de_revue.py) | 8 — transforme l'épinglage `model: opus` et le retrait d'`Edit`/`Write` en **preuve machine** au lieu d'une convention |
| [`docs/metriques-revue.md`](../metriques-revue.md) | 9 — l'instrument de mesure |

⚠️ Cette table nomme des fichiers **vérifiés à la main le 16/08/2026**. Un module nommé ici qui ne
porterait plus rien serait pire que pas de table : elle se relit dans le code du jour, pas dans cet
ADR.

⚠️ **Et rien ne maintiendra vraie la moitié de cette table.** `_RACINES_DE_CODE`
(`backend/atlas/sources/adr.py`) ne contient **pas `.claude/`** : toutes les lignes ci-dessus qui
nomment un agent, la commande ou `settings.json` sont **invisibles** au contrôle `portage-inexistant`,
pourtant bloquant en CI. Seules celles qui pointent vers `backend/`, `docs/` et `.github/` sont
confrontées au dépôt. Renommer une grille demain laisserait cette table verte.

C'est la première fois qu'une section « Porté dans le code par » nomme des fichiers hors du périmètre
de l'atlas. La résorption est inscrite en [DETTE-068](../dette.md) et relève d'une US `chore/` sur le
générateur — pas du lot qui a créé le problème (règle 16). En attendant,
`backend/tests/test_agents_de_revue.py` couvre l'essentiel : l'**existence** des cinq grilles et de
la porte, et leurs propriétés de frontmatter.

## Liens

`CLAUDE.md` § Économie de contexte, § Dette, § Workflow ·
[`.claude/commands/revue-us.md`](../../.claude/commands/revue-us.md) ·
ADR-0001 (adopter les ADR) · ADR-0009 (gouvernance des dépendances).
