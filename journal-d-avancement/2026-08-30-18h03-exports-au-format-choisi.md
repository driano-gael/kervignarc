# 30 août 2026, 18h03 — Sortir un document au format qu'on veut

## Ce qui est nouveau

L'écran **« Exports & impressions »** ne propose plus un bouton par document, mais **un bouton par
format**.

| Document | Formats proposés |
|---|---|
| Liste de placement | PDF · **CSV (tableur)** |
| Liste club & paiement | PDF · **CSV (tableur)** |
| Feuille de marque | PDF seul |

Et les **feuilles de marque** arrivent sur cet écran : la fonction existait depuis longtemps côté
serveur, mais **aucun bouton n'y menait**. Il fallait connaître son adresse pour l'obtenir.

## Ce que ça change pour l'organisateur

Jusqu'ici tout sortait en PDF. C'est parfait pour imprimer et afficher à l'entrée du gymnase ; c'est
inutilisable pour **compter**. La liste club & paiement, en particulier, n'était qu'une image :
pour pointer les chèques, additionner ce qui reste dû ou envoyer un état à la trésorière, il fallait
tout ressaisir.

Le CSV répond à ce second usage. Ouvert dans Excel ou LibreOffice, il donne **une ligne par archer**,
le club en colonne, et des montants que le tableur sait additionner. On trie, on filtre, on
sélectionne un club, on fait la somme — tout ce qu'un PDF interdit.

Le PDF, lui, **n'a pas bougé d'un pixel** : mise en page, regroupements par club et ligne de total
sont identiques.

## Un détail qui n'en est pas un

Un fichier CSV « techniquement correct » s'ouvre très souvent en bouillie : accents transformés en
charabia, ou toutes les données tassées dans la première colonne. Trois réglages, invisibles mais
décisifs, ont été faits pour que le fichier **s'ouvre correctement d'un double-clic**, sans passer
par un assistant d'importation. Le scénario de recette
([`docs/fonctionnel/E16US007.md`](../docs/fonctionnel/E16US007.md)) demande explicitement de le
vérifier : c'est le genre de défaut qu'on ne découvre qu'en salle, le jour où on en a besoin.

## La feuille de marque n'a qu'un format, et c'est voulu

Elle ne propose que le PDF. Ce n'est pas un oubli : une feuille de marque se remplit **au stylo, sur
la cible**. Un CSV n'aurait aucun usage. C'est justement ce contraste qui montre que la liste des
formats est **propre à chaque document**, et non une liste unique appliquée partout.

## Aussi dans cette livraison

Vous avez tranché une question laissée ouverte le 29 août : **l'organisateur peut désormais déclarer
lui-même l'abandon d'un archer en qualification**, depuis la fiche de l'archer, sans aller chercher
un scoreur. C'est le même geste que celui déjà ouvert sur les duels, et il passe par la **même fenêtre de
confirmation** : elle nomme l'archer et vous prévient **avant** le clic.

L'**annulation** d'un abandon reste, elle, dans l'espace du scoreur — c'est le seul écran qui
affiche le classement, donc le seul qui sache dire *qui* est déjà déclaré forfait. C'est une limite
assumée : vous pouvez déclarer sans pouvoir défaire depuis cet écran.

## Ce qui reste dû sur les exports

- Le **classement (palmarès)** ne sort qu'en PDF. L'ouvrir aux autres formats demande de changer une
  adresse **publique**, ce qui appelle votre arbitrage.
- Le **journal d'audit** n'est consultable **nulle part** : la fonction existe côté serveur, mais aucun écran ne l'affiche. (Nous avions d'abord cru le contraire ; la relecture l'a corrigé.) Il faut donc l'écran **puis** l'export.
- Le format **Excel (`.xlsx`)** n'est pas proposé : il faudrait ajouter une bibliothèque au logiciel,
  décision qui vous revient. En attendant, **Excel ouvre les CSV**.

Ces trois points sont réunis dans une fiche dédiée (`E16US016`) pour ne pas se perdre.
