# 30 juillet 2026, 10h02 — « Où tire-t-on ensuite ? » sur la tablette de la cible

**Pour l'archer, au moment où il s'en va.** Le tour précédent avait livré le **geste** de
l'organisateur (le feu vert, puis « Lancer »). Il manquait ce que l'archer, lui, voit. C'est ce que
livre cette tâche : le **premier des quatre écrans** qui reçoivent ce signal — celui qui est déjà
sous sa main.

**Ce qui est nouveau.** La tablette de la cible a désormais un second visage. Quand les tirs sont
finis et validés, elle bascule d'elle-même sur **« Où tire-t-on ensuite ? »** : pour **chaque**
archer, sa **cible** et sa **place** en gros caractères — « Cible 4 · place B » — avec, en dessous,
le tour et le nom de l'adversaire. Un bouton **« Retour à la grille »** ramène à la saisie, et le
panneau reste consultable tant que la cible a fini.

Le même panneau s'affiche côté **duels** : dès que le scoreur valide un duel, il voit les **deux**
duellistes routés — le vainqueur vers son prochain rendez-vous, le battu vers sa sortie (« Éliminé —
Quart de finale »), ou vers son rang quand le podium est acquis (« Vainqueur du tableau », « 3ᵉ du
tableau »).

L'affichage est **immédiat** : rien n'est calculé à cette seconde-là. C'est possible parce que les
cibles sont attribuées aux **matchs** — « le match n°3 se tire sur la cible 4 », quel que soit son
vainqueur — donc la destination existe **avant même** que le duel soit joué.

**Ce que l'appli ne sait pas encore, elle l'écrit.** C'est le parti pris de cet écran, et il est
volontaire : plutôt qu'une case vide qu'on prendrait pour une panne, une phrase. « **Cible attribuée
au lancement du tour** » (les cibles des tours suivants ne sont pas encore posées par l'application),
« **en attente du duel n°2** » (l'adversaire sort d'un duel qui n'est pas fini), « **rang publié en
fin de phase** » (l'appli connaît aujourd'hui les quatre premiers du tableau, pas le classement
complet). Elle n'invente jamais une cible ni un rang.

**Et elle se tait plutôt que de se tromper.** Si le classement bouge après que le plan des duels a
été fait — une simple correction de score suffit — les adversaires ne sont plus les mêmes, et la
cible prévue devient fausse. Dans ce cas l'écran n'affiche **pas** l'ancienne cible : il dit
« placement à revoir ». Envoyer deux archers sur deux buttes différentes est précisément l'incident
que cet écran existe pour éviter.

**Ce qui reste à venir.** Les **trois autres canaux** de la même information — l'application publique
sur téléphone, l'écran de salle — recevront le même signal dans leurs propres tâches. Le
**repêchage** (un battu réintégré) n'existe pas encore dans le moteur : le panneau ne l'affiche donc
jamais.
