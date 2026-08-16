# 16/08/2026 — L'avancement, et des documents de suivi qui ne se contredisent plus

L'atlas du projet — le dossier qu'on ouvre d'un double-clic — gagne une page **« L'avancement »**.
On y voit, d'un coup d'œil : les US regroupées par jalon avec leur état, **l'ordre dans lequel les
grands chantiers peuvent s'enchaîner** (un schéma en lignes droites, sans fioriture), la dette
encore ouverte, et une **fiche par US** qui rassemble ce que les quatre documents de suivi en disent
— son état, le chantier auquel elle appartient, les décisions qui la citent, la dette qu'elle a
ouverte ou refermée.

## Ce qui change vraiment

Le suivi du projet vit dans quatre fichiers écrits à la main, qui se citent les uns les autres sans
que rien ne vérifie qu'ils **concordent**. Désormais, l'atlas **refait les comptes lui-même** plutôt
que de recopier ceux qui sont écrits, et **refuse de valider** tant qu'un écart subsiste. Ce n'est
pas de la cosmétique : ce tableau de suivi est le point où l'on reprend le travail. S'il annonce
faux, c'est la séance suivante qui repart sur une base fausse.

## Trois erreurs trouvées le jour même

Aucune des trois ne se voyait à la relecture :

1. un compteur de jalon annonçait **12 US faites sur 15**, alors que son tableau en portait **16,
   dont 14 faites** — l'en-tête n'avait pas suivi le corps ;
2. deux US **réellement livrées** (le Big Shoot Off et le système suisse) n'apparaissaient dans
   aucun tableau compté : elles n'existaient que dans la liste d'attente. Le total affiché en tête
   les comptait, aucun jalon ne les voyait ;
3. deux dettes techniques **différentes** portaient le même numéro sur la branche principale. Deux
   travaux menés en parallèle avaient pris le même numéro libre et, chacun pour éviter de gêner
   l'autre, l'avaient écrit à un endroit éloigné du fichier — si bien que la fusion s'est faite
   sans le moindre signalement.

Les trois sont corrigées. La quatrième du même genre, elle, sera signalée automatiquement.

## Ce que ça ne fait pas

L'atlas ne dit **pas** qu'une US est faite : il rapporte ce que le tableau de suivi écrit, et rien
d'autre. Trois US ont une trace dans l'historique du dépôt sans être livrées — un outil qui
déduirait l'avancement de cet historique les compterait faites, et se tromperait.

## À vérifier

La convention `docs/fonctionnel/` ne s'applique pas ici — elle vise les US qui livrent une surface
dans l'application (`frontend/src/**`), pas l'atlas. La recette tient donc en cinq gestes, à faire
en ouvrant `atlas/index.html` d'un double-clic puis en cliquant « L'avancement » :

1. les quatre cartes du haut annoncent un nombre d'US livrées **identique** à celui écrit en tête
   de `journal-d-avancement/SUIVI-US.md`, et « 0 compteur divergent » ;
2. chaque section porte une pastille **verte** « concorde » ; une pastille rouge signale un
   compteur à corriger, et c'est un défaut, pas un affichage ;
3. le schéma « L'ordre des epics » se lit de gauche à droite, en lignes droites, sans qu'aucun
   trait ne traverse une boîte ; il défile horizontalement dans son cadre sans déborder la page ;
4. un clic sur un identifiant d'US ouvre sa fiche : état, epic, fiche de `stories/`, décisions qui
   la citent, dette introduite ou résorbée ;
5. à **360 px de large** (téléphone), aucune page ne défile horizontalement : seuls les tableaux et
   le schéma défilent, chacun dans son propre cadre.

⚠️ Le point 5 n'a **pas** pu être vérifié à la livraison (la fenêtre du navigateur de ce poste ne
descend pas sous la largeur d'écran). Ce qui est prouvé mécaniquement : aucun débordement de page,
et tout tableau vit dans un conteneur défilant.
