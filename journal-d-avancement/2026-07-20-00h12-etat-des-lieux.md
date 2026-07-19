# État des lieux — 20 juillet 2026, 00h12

*Premier fichier du journal : il ne raconte pas une session, il fait le point sur tout ce que
l'application sait déjà faire à ce jour.*

---

## De quoi parle-t-on ?

**Kervignarc** est un logiciel pour **organiser un tournoi de tir à l'arc en salle** (à 18 mètres)
et le faire tourner le jour de la compétition. Il est prévu pour fonctionner **sur le réseau du
gymnase, sans internet**, avec l'ordinateur de l'organisation d'un côté et une trentaine de tablettes
posées sur les cibles de l'autre.

À ce stade, ce n'est pas encore le logiciel complet, mais **une bonne moitié du parcours est déjà en
place et utilisable**. Voici ce qu'il sait faire.

## Avant la compétition — tout préparer

L'organisateur dispose d'un espace d'administration protégé par mot de passe, avec un menu qui suit
le déroulé naturel d'un tournoi :

- **Créer le tournoi** : lui donner un nom, une date, un lieu, un type. On peut ensuite le modifier,
  le démarrer, le terminer, ou le supprimer — un tournoi passe par des étapes claires (brouillon, en
  cours, terminé) et le logiciel empêche les gestes dangereux (par exemple supprimer un tournoi qui
  est en train de se dérouler). Plusieurs tournois peuvent tourner **en même temps** (par exemple un
  en salle et un en extérieur).
- **Définir les catégories** (par âge, par type d'arc…), avec la possibilité de **charger d'un clic
  les catégories officielles de la fédération** pour le tir en salle, plutôt que de tout retaper.
- **Décrire les cibles en carton (« blasons »)** et les points qu'on peut marquer dessus — car selon
  le blason, toutes les valeurs ne sont pas possibles.
- **Dessiner le plan de la salle** (où sont les cibles), le réutiliser d'un tournoi à l'autre, et
  l'ajuster.
- **Régler les règles de calcul** des scores et le moment où un score est considéré comme validé.
- **Organiser les créneaux de tir (« départs »)**, avec leur tarif et le nombre de places.
- **Tenir le carnet d'adresses des clubs** participants.
- **Gérer les archers** : les créer, les modifier, les inscrire sur un ou plusieurs créneaux, et
  **calculer automatiquement ce que chacun doit payer**.
- **Placer les archers sur les cibles** : le logiciel propose un plan de placement tout seul, et
  l'organisateur peut le retoucher en **glissant-déposant** un archer d'une cible à l'autre.
- **Désigner les personnes qui valideront les scores** (les « scoreurs »), chacune avec son code
  personnel.
- **Rattacher chaque tablette à sa cible** : au montage, on scanne un QR code collé sur la cible et
  la tablette « sait » pour le reste de la journée quelle cible elle sert — même si on ferme l'onglet
  ou si la tablette redémarre, elle **retrouve sa cible toute seule**.

## Le jour J — la saisie des scores

- Une fois la tablette rattachée à sa cible, elle affiche **directement l'écran de saisie**. Un
  archer de la cible (le « marqueur ») tape les flèches pour tout le monde, sur de **gros boutons
  adaptés au tactile**. Le logiciel ne propose que les valeurs réellement possibles sur le blason
  utilisé, et refuse tout score aberrant.
- Chaque volée enregistre **qui l'a saisie et à quelle heure**, on peut la corriger tant qu'elle
  n'est pas validée, et le total se met à jour au fur et à mesure.
- Le scoreur, lui, passe **valider** les séries ; une correction sur un score déjà validé laisse une
  **trace** (qui, quand, avant/après) dans un journal.
- Un **classement en direct** se met à jour tout seul et peut être **suivi par le public** sans avoir
  à se connecter.

## Sous le capot (dit simplement)

Sans entrer dans la technique, trois choix de fond sont déjà en place et se ressentiront le jour J :

- **Le serveur central est le seul juge.** Les tablettes proposent, le serveur décide et enregistre —
  ça évite deux tablettes qui se contrediraient.
- **Les enregistrements se font un par un, à la file**, pour qu'aucun score ne s'écrase à cause de
  deux personnes qui tapent en même temps.
- **Un journal d'audit** garde la mémoire des actions sensibles (validations, corrections).

## Ce qui n'est pas encore là

Ces parties sont **conçues et décidées** mais pas encore livrées comme écrans utilisables :

- Les **phases finales** (les duels en tableau, une fois les qualifications terminées).
- Les **épreuves par équipes**.
- Les **paiements** (au-delà du simple calcul du montant dû).
- Les **exports et documents** de fin (podiums, résultats à imprimer) — la génération de certains
  documents PDF (feuilles de marque, plans de salle) existe déjà, mais pas la chaîne complète.
- La **résilience réseau de la saisie** : si une tablette perd le réseau une minute, mettre ses
  saisies de côté et les renvoyer à la reconnexion. *(C'est le prochain chantier.)*

---

*Prochaine entrée du journal : à la fin de la prochaine session de travail.*
