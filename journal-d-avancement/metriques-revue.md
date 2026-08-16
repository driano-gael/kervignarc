# Métriques de `/revue-us` — journal de mesure

ADR-0013 assume deux inconnues **en toutes lettres** : le chemin critique `max(A, B, C1, C2, D)`
« n'a pas été mesuré », et le gain de ~2× est « une estimation à confirmer sur les trois prochaines
US, pas un acquis ». Ce fichier est l'instrument de cette confirmation — un tableau Markdown, aucune
dépendance, aucun outil (règle 11 : parcimonie ; règle 12 : la rigueur va au moteur métier, pas à
l'outillage).

**Rempli à l'étape 2 de `/revue-us`**, par l'agent auteur, à partir des rapports qu'il a déjà en
main. Une ligne par passe. Le fichier est versionné : il voyage entre les postes, comme tout ce qui
cadre le projet.

## Ce que chaque colonne sert à décider

| Colonne | Question à laquelle elle répond |
|---|---|
| `durée porte` | La porte mécanique vaut-elle son coût avant la revue ? |
| `durée revue` | Le temps mur réel de l'étape 1 (= l'axe le plus lent) |
| `axe le + lent` | **C2 est-il vraiment le chemin critique**, ou est-ce B ou C1 ? La scission C1/C2 repose sur cette présomption non vérifiée |
| `bloquants par` | **La colonne décisive.** Quel axe trouve ce qui compte. Après 8-10 passes, elle dit lesquels méritent leur coût — et si l'axe D reste le seul à trouver des bloquants, elle interdit de le raccourcir |
| `passes` | Nombre d'allers-retours étape 2 → étape 3 avant PR |

⚠️ **Ce qui n'est pas mesuré ici, et pourquoi.** Le **coût en tokens par axe** est hors de portée :
une session ne peut pas lire sa propre consommation ventilée par sous-agent. Le seul instrument
disponible est `/cost`, manuel et à la granularité de la session entière. Ne pas inventer une
colonne « tokens » qu'on remplirait à l'estime : un chiffre faux est pire qu'une case vide.

## Journal

| date | US | fichiers | lignes diff | durée porte | durée revue | axe le + lent | A | B | C1 | C2 | D | bloquants par | passes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| *(première ligne à la prochaine passe de `/revue-us`)* | | | | | | | | | | | | | |

Colonnes `A` / `B` / `C1` / `C2` / `D` : verdict d'axe, noté `OK` ou `bloquant:n majeur:n mineur:n`.
Un axe non lancé se note `—` (l'axe D est facultatif hors changement structurel).
