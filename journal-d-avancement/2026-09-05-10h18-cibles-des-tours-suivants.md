# 5 septembre 2026, 10 h 18 — La fin du tableau cesse de se jouer sur papier

## Ce qui est nouveau

Dans une phase à élimination directe, les archers **changent de cible à chaque tour** : les
demi-finalistes ne tirent pas là où ils ont tiré leur quart, et les deux finalistes viennent de deux
buttes différentes.

Jusqu'à aujourd'hui, l'application ne savait poser que le **premier tour**. Passé celui-ci, tout le
reste du tableau restait marqué « cible non attribuée » : le feu vert ne passait plus jamais au vert,
et l'écran de routage n'indiquait plus à personne où se rendre. Concrètement, **l'organisateur
reprenait le papier pour toute la fin de la journée** — c'est-à-dire pour les quarts, les demies et
la finale, les moments où le gymnase est le plus rempli.

Désormais, **dès que tous les duels d'un tour sont validés, les archers du tour suivant reçoivent
leur cible sans le moindre clic.** Le plan affiche un tour à la fois — celui qui se joue —, et il en
écrit le numéro en haut de l'écran.

## Ce que ça change pour l'organisateur

- **Le feu vert reste utile toute la journée.** Les demi-finales et la finale s'annoncent « prêtes »
  avec leurs cibles, et le bouton de lancement les compte.
- **L'écran de routage envoie chaque archer à la bonne butte**, tour après tour, au lieu de se taire
  après le premier.
- **Les archers se regroupent.** À chaque tour il reste moins de monde : le tableau se resserre vers
  les cibles de plus petit numéro et libère les buttes hautes — la finale se tire devant le public,
  pas au fond de la salle.
- **Vos ajustements tiennent.** La pose automatique ne fait que **remplir les places vides** : elle
  ne redistribue jamais ce que vous avez déplacé à la main au glisser-déposer.

## Deux points à connaître

- **Le premier tour se génère toujours à la main**, avec le bouton « Générer le plan ». C'est
  volontaire : le remplir d'office reposerait un archer que vous auriez délibérément laissé en
  réserve.
- **Pendant une pause programmée, rien ne se pose.** La salle s'arrête ; on ne prépare pas la butte
  suivante pour des archers qu'on vient d'arrêter. La pose se fait à la reprise.

## D'où venait ce trou

Il n'a pas été trouvé en cherchant : il a été rencontré. En préparant une autre demande — pouvoir
choisir qu'un tour se lance tout seul plutôt qu'au clic —, il est apparu que **le lancement
automatique n'aurait rien eu à lancer** : aucun duel n'était jamais prêt après le premier tour. La
demande d'origine a donc été mise en attente, et c'est ce blocage-là qui a été levé d'abord.

La cause était une limite technique jamais présentée comme telle : la table qui retient les
placements ne pouvait mémoriser **qu'une seule cible par archer et par phase**, alors qu'il en faut
une par tour. Un document interne renvoyait par ailleurs vers un travail « à venir » qui était en
réalité **livré depuis six semaines et sans rapport avec le sujet** — de sorte que personne
n'attendait plus rien, et que rien n'avançait.

Recette détaillée : [`docs/fonctionnel/E03US012.md`](../docs/fonctionnel/E03US012.md).
