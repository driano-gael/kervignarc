# Métriques de `/revue-us` — journal de mesure

ADR-0013 assume deux inconnues **en toutes lettres** : le chemin critique `max(A, B, C1, C2, D)`
« n'a pas été mesuré », et le gain de ~2× est « une estimation à confirmer sur les trois prochaines
US, pas un acquis ». Ce fichier est l'instrument de cette confirmation — un tableau Markdown, aucune
dépendance, aucun outil (règle 11 : parcimonie ; règle 12 : la rigueur va au moteur métier, pas à
l'outillage).

**Rempli à l'étape 2 de `/revue-us`**, par l'agent auteur. Une ligne par passe. Registre technique,
au même titre que [`dette.md`](dette.md) et [`dependances.md`](dependances.md) — et non dans
`journal-d-avancement/`, qui est le livrable rendu au commanditaire, en français non technique.

## Ce que chaque colonne sert à décider, et d'où elle vient

| Colonne | Question à laquelle elle répond | Source |
|---|---|---|
| `date` · `US` | Repérage. `US` reste vide sur un lot `chore/` sans identifiant | branche |
| `fichiers` · `lignes diff` | Le temps de revue suit-il la taille du diff ? | `git diff --stat` de l'étape 0.3 |
| `durée porte` | La porte mécanique vaut-elle son coût avant la revue ? | les **deux** horodatages de l'étape 0 (points 1 et 7) |
| `durée revue` | Le temps mur réel de l'étape 1 (= l'axe le plus lent) | la plus longue des lignes `Durée :` des rapports |
| `axe le + lent` | **C2 est-il vraiment le chemin critique**, ou est-ce B ou C1 ? La scission C1/C2 repose sur cette présomption non vérifiée | ligne `Durée :` de chaque rapport (gabarit du préambule) |
| `A`/`B`/`C1`/`C2`/`D` | Verdict par axe : `OK`, ou `bloquant:n majeur:n mineur:n`. `—` si l'axe n'a pas été lancé | synthèse de chaque rapport |
| `bloquants par` | **La colonne décisive.** Quel axe trouve ce qui compte. Après 8-10 passes, elle dit lesquels méritent leur coût — et si l'axe D reste le seul à trouver des bloquants, elle **interdit** de le raccourcir | fusion de l'étape 2 |
| `passes` | Nombre d'allers-retours étape 2 → étape 3 avant PR | comptage |

⚠️ **Ce qui n'est pas mesuré ici, et pourquoi.** Le **coût en tokens par axe** est hors de portée :
une session ne peut pas lire sa propre consommation ventilée par sous-agent. Le seul instrument
disponible est `/cost`, manuel et à la granularité de la session entière. Ne pas inventer une
colonne « tokens » qu'on remplirait à l'estime : un chiffre faux est pire qu'une case vide. La même
exigence vaut pour les autres colonnes — si une source ci-dessus manque, la case reste vide et on le
dit.

## Journal

| date | US | fichiers | lignes diff | durée porte | durée revue | axe le + lent | A | B | C1 | C2 | D | bloquants par | passes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-18 | `E05US031` | 43 | +3064/−177 | ~10 min | ~45 min | D (16:12→16:57) | majeur:2 mineur:2 suggestion:2 | majeur:3 mineur:4 suggestion:2 | **bloquant:1** majeur:3 mineur:5 suggestion:3 | majeur:2 mineur:3 suggestion:2 | majeur:4 mineur:2 suggestion:1 | C1 | 1 |
| 2026-08-16 | — (`chore/agents-dedies-revue`) | 13 | +719/−133 | ~1 min | ~12 min | C2 | bloquant:2 majeur:6 mineur:4 | majeur:5 mineur:5 | majeur:6 mineur:5 | majeur:9 mineur:5 | bloquant:3 majeur:6 mineur:3 | **A (2), D (3)** | 2 |

**Lecture de la première ligne.** Elle contredit déjà une présomption d'ADR-0013 et en confirme une
autre. C2 est bien l'axe le plus lent — la scission C1/C2 tient. Mais les **bloquants** viennent de A
et de D, pas du chemin critique : la vitesse d'un axe ne prédit pas ce qu'il trouve. Et pour la
troisième fois consécutive, l'axe adversarial trouve le plus grand nombre de bloquants — dont deux
qu'aucun axe de conformité n'avait vus.

**Lecture de la deuxième ligne (E05US031).** Trois enseignements, dont deux vont contre la première
ligne.

1. **L'axe adversarial n'a PAS trouvé le bloquant** — c'est C1, un axe de conformité, qui l'a vu
   (un compteur d'archers « encore en lice » qui affichait combien il en resterait à la fin). La
   série « D trouve le plus de bloquants » s'arrête à trois. Ce que D a apporté ici est d'un autre
   ordre : deux défauts de **raisonnement transporté** — une règle juste chez son auteur d'origine,
   réutilisée là où son hypothèse ne tient plus — qu'aucune grille ne décrit.
2. **D reste l'axe le plus lent** (45 min), et de loin, alors que la première ligne désignait C2.
   L'écart tient au périmètre : ici D a relu du code d'appui hors diff pour vérifier une affirmation
   de l'auteur. C'est ce qu'on lui demande ; le chemin critique s'allonge en conséquence.
3. **Les cinq axes ont trouvé, et aucun n'était redondant.** Quatre défauts n'ont été vus que par un
   seul axe : le bloquant (C1), le portage d'ADR hors de portée du vérificateur d'atlas (C2, confirmé
   par D), l'inversion `shared/ → features/` exprimée en CSS (A), et une section de registre décrivant
   une version antérieure de l'US (D). La grille de conformité et l'adversarial ne se recouvrent pas.

⚠️ **Le coût réel de la passe est sous-estimé par la colonne « durée revue ».** Les correctifs ont
demandé une heure de plus que la revue elle-même, l'essentiel étant les **trois fichiers de tests de
montage** qui manquaient (+26 cas). C'est la contrepartie honnête d'un axe B qui fait son travail :
il ne coûte rien à la revue et beaucoup à la correction.
