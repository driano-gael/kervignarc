# 27 juillet 2026, 21h01 — Ouvrir l'appli depuis une tablette, et voir le QR d'une cible à l'écran

**Pour l'organisateur (E11US008).** Deux petits manques repérés à la démo, corrigés ensemble.

**Ouvrir l'appli depuis une autre machine.** Jusqu'ici, en développement, l'application ne
répondait **que sur l'ordinateur qui la faisait tourner** : impossible de l'ouvrir depuis une
tablette du réseau pour tester. C'est réglé — le serveur s'ouvre maintenant **sur le réseau local**
(comme le fera le fichier exécutable du jour J) et **affiche au démarrage l'adresse à taper depuis
une tablette** (par exemple `http://192.168.1.10:8000`). On peut donc enfin essayer le tournoi
depuis un vrai appareil, dans les conditions du jour J.

**Voir le QR d'une cible directement à l'écran.** Le QR qui sert à **rattacher une tablette à sa
cible** existait, mais **seulement dans le PDF à imprimer**. L'écran **Postes de cible** l'affiche
maintenant **à côté du code**, cible par cible : on **touche** le QR pour l'**agrandir** et le
présenter à une tablette, qui le scanne et se retrouve **rattachée à la bonne cible** — sans rien
imprimer. Le QR reste net même en grand (image vectorielle).

**À savoir.** Pour que le QR affiché soit scannable, l'administrateur doit avoir ouvert l'appli
**par l'adresse du réseau** (pas `localhost`) — c'est expliqué dans la procédure de déploiement
(`docs/deploiement.md`). L'impression des étiquettes reste possible : le QR à l'écran vient **en
plus**, il ne la remplace pas.

*Recette de test : [`docs/fonctionnel/E11US008.md`](../docs/fonctionnel/E11US008.md).*
