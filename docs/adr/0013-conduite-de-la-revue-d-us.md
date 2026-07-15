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

## Liens

`CLAUDE.md` § Économie de contexte, § Dette, § Workflow ·
[`.claude/commands/revue-us.md`](../../.claude/commands/revue-us.md) ·
ADR-0001 (adopter les ADR) · ADR-0009 (gouvernance des dépendances).
