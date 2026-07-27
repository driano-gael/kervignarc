# Scorer un duel, du premier set au podium — 27 juillet 2026

Le **scoreur** a désormais son **écran de duel**. Jusqu'ici, le moteur des duels existait (le tableau
se construit, un match se score, le vainqueur avance) mais **sans surface** : rien à l'écran. C'est
fait — et c'est le premier morceau **visible** du chantier « duels ».

Sur son téléphone, une fois sa session ouverte, le scoreur choisit une **phase de tableau** et voit la
**liste des duels groupés par tour** (la finale en haut), chacun avec les deux archers et son état :
*à saisir*, *en cours*, *à valider*, *validé*. Il ouvre un duel, et le score **manche par manche** :
un pavé tactile — qui ne propose que les **valeurs autorisées** du blason — se remplit pour un archer
puis bascule tout seul sur l'autre. Il enregistre la manche, le **score courant** s'affiche, et la
grille avance. Quand un vainqueur se dégage, il **valide** — le duel se **verrouille** et le gagnant
**apparaît au tour suivant**. Une fois tout joué, un **podium** s'affiche.

Deux subtilités du tir à l'arc sont gérées telles quelles : l'**arc à poulies** se score **au cumul**
(pas en sets) — le scoreur n'a rien à choisir, le serveur le sait de l'arme et l'écran s'adapte ; et
l'**égalité** ouvre un **barrage** (une flèche chacun), avec, si les flèches valent pareil, une
**désignation manuelle** du plus près du centre (l'application ne mesure pas la distance).

Comme la saisie de qualification, l'écran **résiste aux coupures** : si le réseau tombe, l'acte est
mis en file et **renvoyé tout seul** au retour, sans doublon. Et il refuse d'écrire sur un duel dont
les adversaires auraient changé (un score de qualification corrigé entre-temps), pour ne jamais
attribuer un tir au mauvais couple.

Ce qu'il reste avant que les duels soient pleinement exploitables le jour J : l'**abandon /
disqualification**, la **bascule de tour** pilotée (feu vert, lancement) et l'affichage au public des
**affectations du prochain tour**.

*(Recette pas à pas : [`docs/fonctionnel/E04US013.md`](../docs/fonctionnel/E04US013.md). Décisions de
scoring : [ADR-0049](../docs/adr/0049-saisie-et-scoring-des-duels.md).)*
