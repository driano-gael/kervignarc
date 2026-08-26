# 26/08/2026 — L'écran du gymnase se règle, et montre tout le monde

Deux remarques que vous aviez faites en relisant les maquettes de l'écran projeté attendaient encore
leur réponse. Elles sont livrées.

## Ce qui est nouveau

**Le classement projeté ne s'arrête plus aux trois premiers.** Ils restent affichés en haut de
l'écran, en permanence, et **tous les autres archers défilent en dessous**, page après page, avec un
compteur (« 2/5 ») qui dit où l'on en est. Jusqu'ici, la liste sortait de l'écran par le bas : sur un
tournoi de 200 archers, la moitié des noms n'apparaissait jamais.

**La vitesse se règle, écran par écran.** Dans la rubrique « Écrans de salle », chaque écran porte
désormais deux champs : combien de **noms par page**, et combien de **secondes** une page reste
affichée. Vous les changez, vous enregistrez, l'écran suit. Aucun développeur dans la boucle.

Et c'est bien **par écran** : le vidéoprojecteur du fond de salle et un téléviseur près de l'accueil
n'ont ni la même image ni la même distance de lecture. Un réglage unique aurait été mauvais pour
l'un des deux.

## Pourquoi ce n'est pas un « défilement » au sens habituel

Vous aviez écrit « défilement de tous les autres archers dessous ». Un vidéoprojecteur n'a **ni
souris ni écran tactile** : un cadre qui défile y serait un cadre que personne ne peut faire bouger.
Le défilement se fait donc par **pages qui tournent toutes seules** — la même forme que les listes de
noms des affectations, que vous aviez déjà validée dans le même questionnaire, compteur de pages
compris.

Sur votre PC et sur les tablettes, en revanche, **rien ne change** : le classement y garde son cadre
qu'on fait défiler à la main, parce que là, c'est le bon geste.

## À vérifier lors du premier essai en salle

Les valeurs livrées — **40 noms par page**, **20 secondes**, **3 lignes de tête** — sont un choix
raisonnable, mais **elles n'ont jamais été essayées sur un vrai vidéoprojecteur**. C'est justement
pour cela qu'elles sont devenues réglables.

Le jour de votre premier essai : allez au fond de la salle, regardez l'écran, et ajustez les deux
champs jusqu'à ce que les noms se lisent de là où vous êtes. Notez les valeurs qui marchent — elles
serviront de point de départ pour les tournois suivants.

Le scénario de test complet est dans `docs/fonctionnel/E16US009.md`.
