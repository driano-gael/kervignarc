# 19/09/2026 — Un tournoi d'essai se jette enfin (et on voit ce qu'on jette)

**Ce qui est nouveau.** Supprimer un tournoi **fonctionne**. Jusqu'à aujourd'hui, essayer de
supprimer un tournoi qui contenait quoi que ce soit — ne serait-ce qu'un créneau — renvoyait une
« erreur serveur » : rien n'était supprimé, et rien n'expliquait pourquoi. C'est la plus ancienne
anomalie du projet, ouverte depuis les premiers écrans de configuration et aggravée par chaque
fonctionnalité ajoutée depuis.

**Pour qui.** L'organisateur, entre deux tournois. Monter une édition d'essai pour prendre l'outil
en main, puis la jeter, redevient un geste normal.

**Ce que ça change concrètement.**

- Un tournoi **sans aucun archer** se supprime d'un clic, même s'il a déjà ses créneaux et ses
  catégories : tout cela se ressaisit, et une fenêtre qui surgit à chaque fois finit par se fermer
  sans être lue.
- Dès qu'un archer est inscrit, une fenêtre annonce **ce qui va disparaître, avec les nombres** :
  « 42 archers, 118 inscriptions, 720 flèches tirées, 8 duels… ». Pas « des données existent » — les
  natures et leurs chiffres.
- Si de l'argent a été encaissé, le **montant est dit en euros** avant de confirmer — en deux
  sommes séparées : ce qui a été **reçu** et ce qui restait **à rendre**. Le registre des
  remboursements appartient au tournoi : il part avec lui, il n'y a donc nulle part où inscrire une
  somme à rendre. À défaut de pouvoir la tracer, l'application la montre — c'est à l'organisateur de
  décider s'il doit rembourser avant d'effacer.
- Un tournoi **préparé mais sans un seul archer** n'est pas « vide » non plus : ses **postes**
  enrôlés et ses **scoreurs** codés sont comptés, parce que leurs codes sont tirés au hasard — les
  QR déjà imprimés et collés sur les buttes ne se retrouvent pas. Même chose pour le **journal
  d'audit** : c'est une trace, rien ne la reconstitue.
- Un tournoi **en cours de tir** reste, lui, **impossible** à supprimer, quoi qu'on confirme. Il
  faut d'abord le terminer ou l'annuler. Ce sont deux refus de natures différentes : l'un est une
  question à laquelle on peut répondre « oui », l'autre pas.
- Le **patrimoine du club** — clubs, modèles de catégories et de blasons — ne part jamais avec une
  édition supprimée.

**Corrigé dans la foulée.** Supprimer une **fiche archer** qui avait payé son inscription effaçait
la somme **sans laisser de trace au registre**. C'était le seul des trois chemins de suppression à
ne rien inscrire ; il ouvre désormais un remboursement à traiter, comme les deux autres.

**Trouvé au passage.** Supprimer un **créneau** sur lequel un arrêt avait été posé partait lui aussi
en erreur serveur — un cas indépendant, jamais rencontré parce que peu fréquent. Corrigé ici.
