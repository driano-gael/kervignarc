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
machine. La liste est **calquée sur `ci.yml`**, l'autorité bloquante ; toute divergence est un bug de
la procédure.

**2. Quatre axes disjoints, relus en parallèle**, à modèle fort — A (architecture & config,
règles 1-8), B (CA/tests/dépendances/front, 9-11 + volet front de 3 et 4), C1 (correction & cas
limites, 13), C2 (dette & conception, 14-16). Le temps mur devient celui de l'axe le plus lent au
lieu de leur somme. Le découpage suit ce que chaque axe doit **lire**. C2 est le chemin critique :
la règle 13 en a été sortie vers C1 pour le raccourcir.

**3. Le périmètre est une aide à la lecture, jamais un déclencheur.** Les règles s'appliquent
toujours. Le court-circuit est réservé aux règles qui détectent une **présence** (10 front,
11 dépendances) et **interdit** à celles qui détectent une **absence** (9 tests, 12 traçabilité).

**4. La sécurité est la seule règle partagée par les quatre axes**, chacun sur son périmètre — le
doublon est voulu.

**5. La décharge est suspendue si le diff touche la configuration des outils.** Une porte verte ne
prouve rien si le diff a déplacé la porte.

**6. La règle 12 se vérifie à l'étape 0**, par l'auteur : elle porte sur la branche et le message de
commit, pas sur un fichier — aucun périmètre de diff ne peut la contenir.

## Conséquences

- **+** Temps mur attendu **~2×** plus court sur le poste le plus lourd du cycle.
- **+** Chaque relecteur traite une consigne courte à fond, au lieu de 16 règles diluées.
- **+** Les preuves machine sont utilisées comme telles, et leurs **limites exactes** sont écrites
  noir sur blanc plutôt que supposées.
- **−** Coût en tokens **~2,5×** : chaque axe lit le diff, plus les préambules, les rapports et la
  passe de fusion. Arbitrage assumé : le temps mur vaut plus que les tokens sur ce projet. **Ne pas
  « optimiser » en refusionnant les axes sans relire cet ADR.**
- **−** Le gain n'est **pas** 3× et ne peut pas l'être : C2 (jugement ouvert + registres) dimensionne
  le chemin critique. Toute annonce supérieure est fausse.
- **−** La décharge est plus étroite que l'intitulé des règles. Résidus explicités, à ne jamais
  perdre de vue : la denylist `_FORBIDDEN_ROOTS` est aveugle aux imports tiers hors liste et au
  caractère synchrone du domaine (règle 1) ; mypy ne dit rien de l'immutabilité et **exclut
  `backend/migrations/`** (règle 4).
- **−** Le découpage crée un **coût de maintenance permanent** : toute règle ajoutée doit se voir
  attribuer un axe *et* un périmètre cohérents. C'est le vrai prix de cette décision, et il a été
  payé dès le premier jet — voir ci-dessous.
- **−** Un défaut né de la **conjonction** de deux axes n'appartient à aucun des deux. C1 en est
  explicitement propriétaire, parce qu'il est le seul à voir le diff entier.

## Retour d'expérience — la première version était cassée

Le premier jet (commit `b47b25c`) a été soumis à sa propre procédure. Résultat : **2 bloquants**,
conservés ici parce qu'ils documentent le mode de défaillance de ce genre de découpage.

- **Les axes découpés par thème de règle, les périmètres écrits par répertoire** — les deux
  découpages ne coïncidaient pas, et tout ce qui échappait tombait dans cet écart : la sécurité
  (règle transversale, axe scopé `backend/`), la traçabilité (règle sur la branche, axe scopé sur
  des fichiers), les tests absents (règle qui détecte un vide, axe déclenché par un plein).
- **Le court-circuit était aveugle au cas « pas de tests »** : une US sans un seul test ne touche pas
  `backend/tests/`, l'axe B répondait « sans objet » sans lire — l'absence de test, c'est-à-dire
  exactement ce que la règle 9 existe pour trouver, était lue comme « rien à faire ».
- **La sécurité, nommée pour éviter le « chacun croit que l'autre le fait », avait été mise dans un
  axe scopé `backend/`** — créant le trou qu'elle voulait fermer, alors que le jeton admin est
  persisté en `localStorage` côté front.

Enseignement retenu et inscrit dans la procédure : **les quatre axes vérifient une conformité, ils ne
cherchent pas à démolir.** Les deux bloquants ont été trouvés par un **agent adversarial** ajouté
hors grille. Sur un changement structurel, cet agent est requis.

## Liens

`CLAUDE.md` § Économie de contexte, § Dette, § Workflow ·
[`.claude/commands/revue-us.md`](../../.claude/commands/revue-us.md) ·
ADR-0001 (adopter les ADR) · ADR-0009 (gouvernance des dépendances).
