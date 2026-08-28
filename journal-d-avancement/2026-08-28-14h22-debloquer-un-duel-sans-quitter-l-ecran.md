# 28/08/2026 — Débloquer un duel sans quitter l'écran

Le « feu vert » — l'écran depuis lequel vous lancez les tours de duels — savait déjà dire **pourquoi**
une ligne n'est pas prête. Il sait maintenant vous donner **le geste qui la débloque**.

## Ce qui est nouveau

**Le duel qui bloque s'ouvre sur place.** Une ligne qui dit « en attente du duel n°3 » porte
désormais un bouton « Voir le duel qui bloque ». Un clic, et vous lisez qui tire ce duel n°3 et sur
quelle cible. De quoi aller chercher les deux archers, ou appeler le bon scoreur, sans quitter
l'écran de lancement.

**Vous pouvez déclarer un forfait vous-même.** C'est le cas qui coûtait le plus cher : un archer est
parti, son duel ne se terminera jamais, et tout ce qui vient après reste bloqué. Jusqu'ici il fallait
trouver un scoreur et lui faire faire la manipulation. Le bouton est maintenant sur la ligne, avec
une confirmation qui redit ce que ça déclenche.

⚠️ **Un point d'honnêteté sur cette livraison** : le serveur accepte désormais aussi qu'un
administrateur **annule** un forfait de duel, mais **aucun écran ne propose encore ce geste**. La
confirmation vous l'annonce avant que vous cliquiez, pour que la surprise n'arrive pas après. Un
forfait de duel déclaré par erreur ne se répare donc pas depuis l'application aujourd'hui : l'écran
qui le permettra fera l'objet d'une évolution à part.

**« Cible non attribuée » vous emmène au bon endroit** — la rubrique « Plan de duels », sur le bon
tournoi, sans le resélectionner.

## Une limite dite plutôt que masquée

Au **deuxième tour et au-delà**, l'application ne sait pas encore placer les archers sur les cibles.
La ligne l'écrit noir sur blanc au lieu d'offrir un bouton qui n'aurait rien pu faire :

> Les cibles ne sont posées qu'au premier tour : ce duel ne peut pas encore partir d'ici.

C'est un choix délibéré. Un bouton inerte vous aurait fait chercher l'erreur de votre côté pendant
que la salle attend. La limite sera levée avec le placement des tours suivants.

⚠️ **Cette limite touche aussi le forfait ci-dessus**, et il faut le dire clairement, parce que ce
que vous verrez à l'écran peut donner l'impression que le geste n'a pas porté. Une ligne bloquée
attend **un ou deux** duels précédents selon le tirage, et elle n'est jamais au premier tour.
Déclarer un forfait en tranche **un** : si elle en attendait deux, elle continue d'attendre l'autre ;
s'il n'en restait qu'un, elle affiche « cible non attribuée ». Quant au compteur du bouton
« Lancer », il **diminue** si le duel que vous venez de régler était lui-même prêt à partir, et **ne
bouge pas** sinon. **Votre geste a porté dans tous les cas** : il a fait avancer le tableau. Tant que
le placement des tours suivants n'est pas livré, le forfait depuis le feu vert sert à **débloquer la
suite du tableau**, pas à faire partir ce duel-là.

## Ce qui n'est pas dans cette livraison

Vous aviez aussi demandé que le lancement puisse être **automatique** — qu'un tour parte tout seul
dès que les conditions sont réunies, sans clic. C'est un vrai changement de mécanique (aujourd'hui,
personne ne vérifie les conditions tant qu'un organisateur ne regarde pas l'écran), et ça part donc
en tranche séparée. Le lancement reste manuel, comme avant.

Le scénario de test complet est dans `docs/fonctionnel/E16US008.md`.
