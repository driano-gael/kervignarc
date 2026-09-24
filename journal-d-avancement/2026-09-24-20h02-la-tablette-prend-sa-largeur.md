# 24 septembre 2026, 20 h 02 — la tablette de saisie prend sa largeur

Les **neuf écrans de l'appli de saisie** n'avaient jamais été comparés aux planches que vous aviez
validées. Seule l'administration l'avait été. C'est fait, et **cinq écrans ont été corrigés**.

## Ce qui change pour le bénévole qui saisit

- **Le pavé de saisie ne s'ouvre plus hors de l'écran.** Toute la saisie tenait dans une colonne de
  640 px au milieu d'une tablette de 1280 : près de la moitié de l'écran restait vide, et le pavé se
  retrouvait **sous** la grille des quatre archers, donc invisible. Chaque archer commençait par un
  défilement — pour un geste qui se répète environ **4 300 fois par départ**. La grille et le pavé
  sont maintenant **côte à côte**. *(Sur un écran plus étroit qu'une tablette en paysage — un
  téléphone, ou une tablette tenue en portrait — ils restent empilés : ce cas-là n'est pas traité.)*
- **Le cumul de l'archer ne reste plus à zéro.** Il ne comptait que les volées déjà contresignées
  par le scoreur — qui ne passe qu'à la fin de la série. Le rappel que vous aviez demandé
  (« en permanence, c'est un bon rappel sur la cible ») affichait donc **0** pendant toute la série.
  Il compte désormais ce qui est saisi.
- **Le « hors ligne » se voit.** C'était une pastille de la taille d'un grain de riz, en haut à
  droite. C'est maintenant un **bandeau ambre plein sur toute la largeur**, qui dit la seule chose
  utile : *la saisie continue, ce qui est tapé part tout seul au retour du réseau*. *(Sur la tablette
  de cible **seulement** : c'est le seul appareil qui met vraiment les saisies de côté. Le promettre
  ailleurs aurait été un mensonge.)*
- **Rattacher la tablette** se fait dans une colonne centrée qui pose une question — « Quelle
  cible ? » — au lieu d'une petite carte dans l'angle. Le bouton « Rattacher cet appareil » était
  écrit **plus petit que chacune des touches** du pavé juste au-dessus ; il est désormais le plus
  gros élément de l'écran. Et une fois rattachée, la tablette affiche **son numéro de cible en très
  gros** : c'est le seul moyen de repérer une tablette posée devant la mauvaise cible avant que
  quelqu'un ait tiré.
- **Choisir le marqueur** ne se fait plus devant une liste nue de quatre noms : une phrase dit ce
  que vous engagez — son nom accompagne chaque volée, c'est la première marque que le scoreur vient
  contresigner, et les volées déjà saisies gardent le nom de qui les a entrées.

## Ce que la comparaison a révélé, au-delà des écrans

Deux constats méritent votre attention, parce qu'ils ne se corrigent pas en programmant.

- **Trois écrans n'ont plus de base de comparaison.** Les questionnaires ont été remplis le 4 août
  sur des **vignettes**, et les planches ont été **redessinées le lendemain** en écrans pleins. Sur
  quatre planches de saisie sur neuf, la proposition que vous aviez retenue n'est plus celle que
  porte sa lettre — et sur l'écran de rattachement, les lettres sont même **inversées**. Pour
  `S04 · marqueur`, `S05 · saisie de duel` et `S08 · validation de cible`, il n'y a donc **plus
  d'étalon** : s'y aligner reviendrait à deviner ce que vous vouliez. `S05` et `S08` n'ont pas été
  touchés. **Sur `S04`, une seule chose a été ajoutée** — la phrase qui explique à quoi sert le
  marqueur. Elle est identique dans les deux versions de la planche, donc elle ne choisit aucune
  forme ; elle vous est soumise comme **proposition**, à confirmer au tour 2. ⚠️ Elle a tout de même
  un effet à juger : le panneau est devenu plus haut, et c'est justement « l'espace volé au pavé »
  que la planche vous demandait d'arbitrer. Le questionnaire du **tour 2** referme le point.
- **`S07 · la file du scoreur` n'existe pas.** Pas « pas conforme » : **pas construit du tout**, ni à
  l'écran ni côté serveur. Un tri antérieur l'avait rangé parmi les écrans « validés, rien à faire »
  — son verdict était pourtant « validé tel quel, **on peut coder ça** », ce qui est un feu vert, pas
  un constat. Votre critique de `S05` (« trop tassé », « sur deux hauteurs plutôt que deux colonnes »)
  est dans le même cas : elle n'est portée par aucune tâche. **Les deux sont désormais inscrits au suivi, en attente de votre arbitrage** — ce ne sont pas des écarts de ressemblance, donc ils ne relèvent pas de ce chantier-ci : il reste à décider où les ranger.

## Ce qui reste à faire sur cet axe

Sur la planche, la ligne de chaque archer porte **les trois flèches de la volée en cours**, et on
tape directement dessus. C'est ce que vous aviez demandé : *« l'appel du pavé doit se faire à la
sélection de la zone de saisie »*. Aujourd'hui, on touche **le nom de l'archer**.

Ce changement a été **écarté volontairement** de cette livraison, mais pas pour la raison que
j'avais d'abord écrite. J'avais invoqué un risque technique daté d'août — vérifier ses volées
effaçait alors les flèches qu'on venait de taper. **La relecture a établi que ce risque n'existe
plus** : le correctif qui l'a supprimé est en place depuis. Le vrai motif est le **périmètre** :
déplacer la saisie dans la ligne de l'archer, c'est redessiner l'écran le plus utilisé du produit,
pas le rapprocher de sa planche — et c'est ce que fait un chantier à part. C'est aussi lui qui
rendra à la grille **toute** la largeur de la tablette : tant que le pavé porte seul la saisie, il
lui faut une colonne prise sur la grille.
