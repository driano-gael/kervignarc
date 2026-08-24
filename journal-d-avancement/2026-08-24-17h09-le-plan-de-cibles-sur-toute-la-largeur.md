# 24 août 2026, 17 h 09 — Le plan de cibles sur toute la largeur, et la réserve sous la main

**Ce que ça change pour l'organisateur.** L'écran où l'on ajuste qui tire sur quelle cible tenait
jusqu'ici dans une mosaïque de petites vignettes : quatre couloirs empilés à la verticale dans
16 centimètres de large, des noms coupés, et aucun alignement d'une cible à l'autre. Il occupe
maintenant **une ligne par cible**, sur toute la largeur de l'écran, les couloirs A à D côte à côte
et alignés d'une ligne sur l'autre.

**Et surtout, on voit sur quoi on arbitre.** Chaque archer affiche désormais, sous son nom, son
**club**, sa **catégorie** et le **blason** sur lequel il tire. Ce sont précisément les trois
informations qui décident des deux avertissements que l'écran posait déjà : « mixité de club non
garantie » et « cloisonnement non respecté ». Ils désignaient une cible sans jamais dire lequel de
ses quatre occupants en était la cause — il fallait quitter le plan pour aller le chercher. La cause
se lit maintenant sur la ligne elle-même. Un archer dont le club n'a pas été renseigné le dit en
toutes lettres : « club inconnu », jamais « aucun club » — à la fédération, tout licencié en a un.

**La réserve devient un vrai puits.** Elle est passée du pied de page à un **panneau à droite qui
reste en place** quand on fait défiler les cibles. La raison est concrète : quand on tient un jeton
à la souris, la page ne défile pas toute seule. Avec une réserve tout en bas, sortir un archer de la
cible 37 obligeait à faire défiler d'abord, à le perdre de vue, puis à recommencer — soit exactement
le geste que votre remarque sur la maquette demandait de rendre facile.

**Le plan de duels a suivi le même chemin.** Votre remarque ne visait que le placement de
qualification, mais les deux écrans sont des jumeaux, utilisés par la même personne sur le même
ordinateur : n'en corriger qu'un aurait donné deux écrans qui se ressemblent presque, ce qui est
plus déroutant que deux écrans identiques.

**Deux des trois demandes étaient déjà satisfaites.** En relisant la fiche avant de coder, il est
apparu que le « puits de réserve » existait déjà — zone, dépose, reprise, et même la distinction
demandée entre « je l'ai mis de côté » et « l'application n'a pas pu le placer » —, et que
« un recalcul ne défait pas les placements manuels » l'était aussi, par le bouton « Placer les
restants ». Ces deux points n'ont donc rien coûté : ils ont gagné des tests qui les protègent
désormais d'une régression. Le travail réel portait sur la mise en page, et sur ce qu'elle permet
enfin de montrer.

*Aucune règle de placement n'a changé : les mêmes déplacements sont acceptés, les mêmes refusés,
avec les mêmes messages. Recette détaillée dans [`docs/fonctionnel/E16US005.md`](../docs/fonctionnel/E16US005.md).*
