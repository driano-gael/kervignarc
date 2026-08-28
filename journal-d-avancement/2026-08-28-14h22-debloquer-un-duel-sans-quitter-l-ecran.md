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
une confirmation qui redit ce que ça déclenche. Et parce qu'une action qu'on ne peut pas défaire est
un piège, l'annulation s'ouvre en même temps.

**« Cible non attribuée » vous emmène au bon endroit** — la rubrique « Plan de duels », sur le bon
tournoi, sans le resélectionner.

## Une limite dite plutôt que masquée

Au **deuxième tour et au-delà**, l'application ne sait pas encore placer les archers sur les cibles.
La ligne l'écrit noir sur blanc au lieu d'offrir un bouton qui n'aurait rien pu faire :

> Les cibles ne sont posées qu'au premier tour : ce duel ne peut pas encore partir d'ici.

C'est un choix délibéré. Un bouton inerte vous aurait fait chercher l'erreur de votre côté pendant
que la salle attend. La limite sera levée avec le placement des tours suivants.

## Ce qui n'est pas dans cette livraison

Vous aviez aussi demandé que le lancement puisse être **automatique** — qu'un tour parte tout seul
dès que les conditions sont réunies, sans clic. C'est un vrai changement de mécanique (aujourd'hui,
personne ne vérifie les conditions tant qu'un organisateur ne regarde pas l'écran), et ça part donc
en tranche séparée. Le lancement reste manuel, comme avant.

Le scénario de test complet est dans `docs/fonctionnel/E16US008.md`.
