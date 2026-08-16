# 16/08/2026 — La carte du code

L'atlas gagne une page **« La carte du code »**. Jusqu'ici il lisait des **documents** : les règles,
les décisions, les tableaux de suivi. Il lit maintenant le **code lui-même**, et le confronte à ce
que l'architecture annonce.

## Ce qui change vraiment

Le projet s'est donné une règle de construction : les dépendances **pointent vers le cœur métier**.
L'affichage peut s'appuyer sur le métier, jamais l'inverse — c'est ce qui permet de changer une base
de données ou un écran sans toucher aux règles de tir à l'arc. Cette règle était vérifiée
automatiquement **pour le cœur métier seulement**. Les quatre autres sens ne l'étaient par rien :
une couche pouvait en appeler une qu'elle n'a pas le droit d'appeler, et **rien** — ni les
vérifications avant enregistrement, ni le contrôle automatique, ni la relecture — ne l'aurait vu.

C'est fait : la carte compte les 827 liens entre les morceaux du programme, les affiche en tableau
et en schéma, et **refuse de valider** si l'un d'eux remonte le courant. Aujourd'hui aucun ne le
fait — la vérification arrive donc à temps pour verrouiller ce qui est encore sain, plutôt que pour
constater des dégâts.

La page montre aussi les **60 « prises »** du programme — les endroits prévus pour brancher une
variante (une autre base, un autre mode de calcul) — et, en face, ce qui y est effectivement
branché.

## Ce que la mesure a trouvé du côté des écrans

L'application côté tablette est découpée en **44 morceaux** censés être indépendants. Ils ne le sont
plus : **142 liens** les relient, et surtout ils forment **quatre nœuds** où chacun dépend des
autres en cercle — dont un seul nœud qui en emprisonne **19 sur 44**. Concrètement, aucun de ces 19
morceaux ne peut plus être lu, testé ou remplacé sans les 18 autres.

Rien n'est corrigé ici : cette page **mesure**, elle ne répare pas. Quatre chantiers ont été écrits
et rangés dans la liste des travaux possibles — dénouer les nœuds, alléger les quatre plus gros
écrans, sécuriser le dialogue entre les écrans et le serveur, et faire relire par les outils les
1 800 lignes du site de l'atlas. **Aucun n'est engagé** : ils attendent votre arbitrage, et l'un
d'eux demande une décision avant même d'être commencé.

## Ce que ça ne fait pas

Le côté serveur est lu **exactement** ; le côté écrans est lu **approximativement**, faute de savoir
analyser ce langage-là sans ajouter d'outil extérieur — un principe du projet est de n'en ajouter
aucun sans nécessité. C'est écrit sur la page : les constats côté écrans sont des **signalements**,
jamais des blocages. Un chiffre y est une tendance, pas une preuve.

## À vérifier

La convention `docs/fonctionnel/` ne s'applique pas ici — elle vise les US qui livrent une surface
dans l'application, pas l'atlas. La recette tient en cinq gestes, en ouvrant `atlas/index.html` d'un
double-clic puis en cliquant **« La carte du code »** :

1. les quatre cartes du haut annoncent **0** dépendance à contresens, **60** prises, **44** morceaux
   d'écran et **4** nœuds — dont le plus gros à **19** ;
2. le schéma du haut se lit de gauche à droite ; **toutes les flèches pointent vers la gauche** (le
   cœur métier est la boîte de gauche, encadrée). Une flèche rouge signalerait une règle enfreinte ;
3. dans le tableau « Couche par couche », les cases marquées **✕** sont vides, et les cases avec un
   nombre ne sont jamais rouges ;
4. dans « Paquet par paquet », déplier « N fichiers » sur n'importe quelle ligne affiche bien la
   liste des fichiers concernés — un nombre qu'on ne peut pas aller vérifier ne sert à rien ;
5. tout en bas, la liste des morceaux d'écran nomme `competition` (importée par 18 autres) et
   `departs` (17) comme **briques communes de fait**.

⚠️ Deux points n'ont **pas** pu être vérifiés à la livraison sur ce poste : l'affichage réel de la
page (le navigateur d'ici refuse d'ouvrir un fichier local) et le rendu à 360 px de large. Ce qui
est prouvé mécaniquement : la page ne charge aucune ressource extérieure, ne dépend d'aucun
mécanisme bloqué au double-clic, et tous ses tableaux vivent dans un cadre défilant. **Un coup
d'œil humain reste nécessaire.**
