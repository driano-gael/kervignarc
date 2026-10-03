# 03/10/2026 — Restaurer une sauvegarde, arrêter proprement (E11US006)

**Ce qui est nouveau.** Dans l'administration, axe « Atelier », un écran **« Sauvegardes »** liste
les copies que le serveur prend toutes les 15 minutes. Chacune se **vérifie** d'un geste (n'est-elle
pas abîmée ? vient-elle bien de cette version de l'application ?), puis se **restaure** après
confirmation, **sans redémarrer le serveur**.

**Pour l'organisateur.** Une fausse manipulation en plein tournoi se rattrape en une minute, sans
fermer l'application ni toucher à un fichier. L'état d'avant la restauration est mis de côté et
apparaît dans la liste : on peut **annuler** en le restaurant. Une copie abîmée est refusée et rien
n'est touché. Après une restauration, les tablettes et les scoreurs se reconnectent.

**Arrêt.** Fermer la fenêtre du serveur par sa croix attend désormais que les saisies en cours soient
enregistrées — comme Ctrl+C le faisait déjà.

**Limites.** La restauration remet **tous** les tournois en arrière, pas un seul. Une copie d'une
version plus ancienne de l’application se restaure encore à la main, selon le guide de déploiement.
La croix laisse au plus quelques secondes aux saisies en attente : au-delà, préférer Ctrl+C.
