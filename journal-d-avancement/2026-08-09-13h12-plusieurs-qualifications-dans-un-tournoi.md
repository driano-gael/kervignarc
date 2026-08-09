# 9 août 2026, 13 h 12 — plusieurs tours de qualification dans un même tournoi

**US : E05US025** · [ADR-0082](../docs/adr/0082-plusieurs-qualifications-dans-un-meme-deroule.md)
· [fiche de recette](../docs/fonctionnel/E05US025.md)

## Ce qui ne marchait pas

Un tournoi ne pouvait comporter **qu'un seul** tour de qualification. Composer le format demandé
le 8 août — 120 archers tirent 3×20, puis la moitié haute et la moitié basse rejouent 3×15 chacune —
était tout simplement refusé par l'application.

Ce n'était pas une règle du tir à l'arc. C'était un garde-fou posé quelques semaines plus tôt pour
contourner un défaut : neuf endroits du code lisaient « **la** » qualification du tournoi, et deux
d'entre eux ne désignaient pas la même. Plutôt que de réparer ces neuf lecteurs, on avait interdit
le cas qui les mettait en défaut. Le commanditaire a demandé le cas.

## Ce qui change

L'organisateur compose autant de tours de qualification qu'il veut, et **chacun a ses propres
réglages**.

- **Chaque tour a son barème.** L'écran « Barème & validation » liste désormais une section par
  qualification : 3×20 pour le premier tour, 3×15 pour la haute et la basse. Régler l'un ne touche
  pas les autres. *Sur un tournoi ordinaire — un seul tour —, l'écran est exactement celui d'avant.*
- **Chaque archer a une feuille de marque par tour.** Une flèche du second tour ne peut plus
  atterrir dans la feuille du premier : le score du tour précédent reste intact, et l'écran de
  saisie ne montre que le tour en cours.
- **Le classement final va de 1 à 120.** La haute occupe les places 1 à 60, la basse les places 61
  à 120. Conséquence à connaître, et voulue : **le premier de la basse reste derrière le dernier de
  la haute, même s'il a mieux tiré son second tour.** La place est décidée par le tour qui a réparti
  les archers, pas par les points marqués ensuite.
- **Aucune médaille n'est décernée par une qualification.** Un tour de qualification classe ; l'or,
  l'argent et le bronze se jouent en finale et en petite finale. Sans cette distinction, un tournoi
  fait de trois qualifications d'affilée aurait remis un podium complet avant le moindre duel.
- **« Prêt à terminer ? » regarde les trois tours**, chacun sur ses propres archers. Un archer
  éliminé à la coupe ne bloque donc jamais la suite.

## Un défaut ancien corrigé au passage

Un archer inscrit sur **deux créneaux** (le matin et l'après-midi) n'avait jusqu'ici qu'un seul
emplacement pour ses flèches : sa seconde feuille écrasait la première. C'était un défaut connu et
inscrit au registre depuis le 6 août. Il disparaît sans travail supplémentaire — rattacher la
feuille au tour de tir la rattache du même coup au créneau.

## Ce qui reste à faire

- **Le plan de cibles reste commun aux trois tours** : les archers ne changent pas de cible entre le
  premier tour et le second. C'est suffisant pour ce format ; un format qui exigerait de replacer
  tout le monde entre deux tours demanderait une évolution.
- **Corriger une feuille depuis l'écran d'administration**, pour un archer inscrit sur deux
  créneaux, écrit dans son créneau du matin. Le chemin normal — la saisie depuis un poste, qui sait
  où il est — n'a pas cette limite.
- Les **poules, le système suisse, la colline et le Big Shoot Off** ne sont toujours pas jouables :
  c'est la tranche suivante.

## À vérifier à la recette

Composer le format de l'exemple, faire tirer les deux moitiés en donnant volontairement à un archer
de la **basse** un meilleur score qu'à un archer de la **haute**, et vérifier au palmarès qu'il
reste **derrière**. Puis rouvrir le classement du premier tour et vérifier qu'il n'a pas bougé.

Le détail pas à pas est dans la [fiche de recette](../docs/fonctionnel/E05US025.md).
