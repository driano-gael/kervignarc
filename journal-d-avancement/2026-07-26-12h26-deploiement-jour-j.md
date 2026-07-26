# 26/07/2026 — Un seul fichier à lancer le jour J

Jusqu'ici, faire tourner Kervignarc demandait une machine « de développeur » : installer Python,
Node, construire le front, lancer des commandes. Ce n'est pas envisageable le matin d'un tournoi.

Désormais, l'application se fabrique en **un exécutable unique** (`kervignarc.exe`) qui contient
**tout** — l'interface, la base de données, la génération des PDF. On le copie sur l'ordinateur du
club, on le lance :

- au **premier démarrage**, il **crée sa base de données** tout seul (vide, prête à l'emploi) ;
- il s'ouvre sur le **réseau local**, accessible depuis toutes les tablettes ;
- il s'annonce sous un **nom simple à retenir** — `kervignarc.local` — en plus de son adresse IP.

Concrètement, le jour J : un routeur Wi-Fi dédié, l'ordinateur du club qui lance le fichier, et les
tablettes qui ouvrent `http://kervignarc.local:8000` (ou l'adresse affichée à l'écran). **Aucune
installation, aucun internet.**

La marche à suivre complète (fabriquer le fichier, brancher le réseau, connecter les tablettes, les
pièges à éviter) est écrite dans [`docs/deploiement.md`](../docs/deploiement.md).

*Restent à venir sur ce volet : les **sauvegardes automatiques** pendant le tournoi et l'**archive**
de fin d'événement (US suivante).*
