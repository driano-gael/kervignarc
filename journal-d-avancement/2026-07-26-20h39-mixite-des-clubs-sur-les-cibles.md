# 26 juillet 2026 — Le placement mêle les clubs sur chaque cible

Quand l'application répartit automatiquement les archers sur les cibles, elle **cherche désormais à ne
pas laisser un seul club occuper une cible entière** : à chaque cible, elle essaie de réunir **au moins
deux clubs différents**. C'est une question d'équité, et c'est fait **sans rien casser** — jamais un
archer n'est écarté juste pour ça, et les règles importantes (la place disponible, la hauteur de la
butte pour les jeunes) passent toujours avant.

**Quand ce n'est pas possible, l'application le dit.** Si une cible ne peut réunir qu'un **seul club**
— ou si le **club de certains archers n'est pas renseigné** —, elle l'affiche clairement : un petit
libellé ambre **« mixité de club non garantie »** sous la cible concernée, et une **bannière
récapitulative** en haut de l'écran de placement (« 1 cible sans mixité de club garantie… »). Ce n'est
**pas une erreur** : l'organisateur voit d'un coup d'œil les cibles à regarder, et décide s'il déplace
des archers à la main.

Point de prudence assumé : deux archers **sans club connu** ne sont **jamais supposés** du même club
(ni du contraire). L'application ne devine pas — elle signale, plutôt que de se tromper en silence.

*Sous le capot : le moteur de placement n'a pas changé ; la mixité est obtenue en présentant ses
archers dans un ordre qui alterne les clubs, et le signalement est recalculé à chaque affichage. Reste
à venir sur ce volet : la séparation catégorie/blason et le placement des duellistes côte à côte.*
