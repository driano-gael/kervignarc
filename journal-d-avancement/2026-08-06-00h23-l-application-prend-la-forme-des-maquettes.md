# 6 août 2026, 00 h 23 — L'application prend la forme des maquettes

La veille au soir, l'application avait pris **les couleurs** du club. Il lui restait la mauvaise
**silhouette** : des angles arrondis deux fois trop, des boutons d'action à la graisse d'un texte
ordinaire, des étiquettes d'état de la taille d'un mot courant. On reconnaissait la charte sans
reconnaître l'écran.

Les composants partagés — boutons, champs, cartes, onglets, étiquettes, en-têtes de tableau —
reprennent désormais les valeurs des planches. Comme ils sont partagés, l'effet porte sur toutes les
pages à la fois. Il y avait bien un système derrière ces chiffres, qu'on a fini par comprendre :
**l'ossature s'arrondit franchement, le contenu très peu**. L'application appliquait le même arrondi
partout, d'où cette impression générale de « pas la même appli ».

**Deux choses n'ont volontairement pas été reprises.** L'**espacement** d'abord : les planches sont
plus serrées, mais vous aviez demandé l'inverse — « je mettrai plus d'espace, plus aéré, et cela pour
tous les écrans ». L'application reste donc plus aérée que la planche, et c'est la planche qui est en
retard. Les **tableaux** ensuite : ils gardent leur structure réelle et n'en prennent que l'apparence,
pour qu'un lecteur d'écran continue d'annoncer le nom des colonnes.

**Cette fois, les écrans ont été ouverts un par un dans un navigateur** — et c'est ce qui a payé. Deux
défauts sont apparus, qu'aucun test ne pouvait voir : les descriptions des portes d'entrée s'étaient
mises à crier en gras (une porte est techniquement un bouton, elle avait hérité de la typographie des
boutons d'action), et surtout, sur le tableau de bord, le bouton **« Annuler le tournoi »** en ambre
plein **écrasait** « Marquer prêt ». Le bouton qui annule criait plus fort que le bouton qui avance.
Il est passé en contour ambre : trouvable, plus dominant.

Une découverte a aussi corrigé la méthode pour la suite. Une planche montre **plusieurs propositions**,
et c'est le questionnaire qui dit laquelle vous avez retenue — parfois « **telles que livrées** »,
c'est-à-dire l'écran actuel. C'est le cas de l'**écran de choix d'appareil** : s'aligner sur la
première variante de la planche aurait **défait un écran que vous aviez validé**. On lit donc
désormais le questionnaire avant la planche.

**Un point attend votre avis** : la couleur d'un bouton qui supprime ou annule. La charte n'en définit
aucune ; le choix actuel (contour ambre) est le nôtre. Recette :
[`docs/fonctionnel/E17US002.md`](../docs/fonctionnel/E17US002.md).

**La suite** : les écarts qui restent ne sont plus des composants mais des **écrans** — par exemple la
liste des tournois, que les planches présentent en tableau à colonnes (avancement, ce qui reste) là où
l'application affiche une ligne simple. Ils se traiteront un par un.
