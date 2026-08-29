# 29/08/2026 — Chercher partout, et voir d'avance ce qui bloque

**US livrée : `E16US010`** — trois demandes du questionnaire de maquettes (A02, A09), réunies parce
qu'elles répondent toutes à la même gêne : *découvrir un problème en ouvrant l'écran*.

## Ce qui est nouveau

**La barre de recherche cherche autre chose que des archers.** Une liste déroulante précède le
champ : on choisit **Tournoi**, **Archer** ou **Club**. On tape sans accents ni majuscules —
`leveque` trouve « Lévêque » —, et **un clic ouvre la fiche**. Elle est présente sur tous les axes,
Atelier compris : c'est là qu'on corrige un nom de club.

**Un clic ouvre vraiment la fiche.** C'était le point dur : jusqu'ici rien, dans l'application, ne
permettait de dire « ouvre la fiche numéro 57 ». L'adresse ne savait nommer qu'un écran. Elle nomme
désormais aussi **l'élément ouvert** — ce qui donne, gratuitement, une capacité que personne n'avait
demandée : **l'adresse d'une fiche se copie, se met en favori, survit au rechargement et au bouton
*Précédent***.

**La liste des tournois prévient avant qu'on l'ouvre.** Chaque ligne peut porter une marque, et il y
en a deux, volontairement différentes : « **à compléter** » (il manque quelque chose, mais le
tournoi partirait quand même) et « **ne peut pas démarrer** » (il sera refusé). Passer la souris
dessus donne la raison, **dans les mots exacts** que l'application opposerait au clic. Un tournoi
déjà lancé, terminé ou annulé ne porte aucune marque : il n'a plus rien à préparer.

**Les fiches en double se traitent là où on les voit.** L'écran « Doublons » a disparu du menu. Le
rapprochement se signale **sur la ligne de l'archer**, dans les inscriptions, et se déplie sur place
pour choisir la fiche à garder. Un décompte en tête de liste (« 3 rapprochements de fiches ») garde
la vue d'ensemble que l'écran dédié apportait.

**Pendant le tournoi, une fiche d'archer en consultation.** Chercher un archer en pilotage ouvre une
fiche qui **montre** — catégorie, blason, club, et où il tire créneau par créneau — avec deux gestes
en bas : corriger sa fiche, ou modifier son placement. C'est l'inverse de la préparation, où le
formulaire s'ouvre directement : pendant le tournoi on regarde d'abord.

## Ce qui reste ouvert

**Déclarer un abandon depuis cette fiche n'est pas livré**, et l'écran le dit au lieu d'offrir un
bouton qui échouerait. Cette écriture appartient aujourd'hui à l'espace **scoreur** pour la
qualification ; en duel, l'organisateur peut déjà le faire depuis le feu vert. L'ouvrir aussi à
l'organisateur en qualification est une **décision de rôles**, qui vous revient.

**La vue d'ensemble des doublons a changé de forme.** Vous aviez tranché que l'icône sur la ligne
*remplace* l'écran dédié plutôt que de s'y ajouter. Le décompte en tête de liste compense, mais on
ne voit plus toutes les paires côte à côte : si cela manque à l'usage, c'est à rouvrir.

*Scénario de recette : [`docs/fonctionnel/E16US010.md`](../docs/fonctionnel/E16US010.md).*
