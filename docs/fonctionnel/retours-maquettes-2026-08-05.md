# Retours du questionnaire de maquettes — lot « front seul » du 05/08/2026

> Documentation fonctionnelle — **scénario de test pour un utilisateur non technique**.
> Objectif : vérifier, écran par écran, que le produit s'est bien aligné sur les réponses du
> questionnaire de maquettes du 04/08/2026. Suivez les étapes dans l'ordre ; comparez ce que vous
> voyez au « résultat attendu ».
>
> ⚠️ **Ce document ne couvre pas tout le questionnaire.** Il décrit ce qui a été livré **sans
> décision à prendre**. Ce qui exigeait un arbitrage ou une évolution du moteur est spécifié dans
> [`stories/E16`](../../stories/E16-retours-maquettes.md) et n'est **pas** encore livré : ne le
> cherchez pas ici.

## Pré-requis
- L'application est ouverte sur un **ordinateur** pour les scénarios 2 à 5, et sur un **téléphone**
  (ou une fenêtre étroite) pour le scénario 6.
- Un tournoi existe, avec au moins un départ et quelques archers placés.

---

## Scénario 1 — Cinq portes, et les bons mots (A00)

1. Ouvrez l'application sur un appareil neuf (ou utilisez « Changer de rôle » en haut à droite).
   → *Résultat attendu :* **cinq** portes et non quatre. Dans l'ordre : **Écran de cible**, **Écran
   de salle**, **Public**, **Scoreur**, **Administration (PC)**.
   → Les mots ont changé : plus de « tablette de cible » (ce peut être un téléphone), plus de
   « téléphone (public) » (ce peut être une tablette d'accueil).

2. Touchez **Écran de salle**.
   → *Résultat attendu :* l'adresse devient `/salle`, le titre affiche **« Écran de salle »**, et le
   texte parle du **code de l'écran de salle** — pas de « votre cible ».

3. Revenez en arrière et touchez **Écran de cible**.
   → *Résultat attendu :* l'adresse devient `/cible`, et le texte parle du **code de votre cible**.

> À retenir : les deux portes mènent au **même mécanisme** de rattachement (même code, même
> fonctionnement). Seuls les mots changent — c'est voulu.

---

## Scénario 2 — Le code d'abord, et un pavé sans pièges (S01)

1. Sur l'écran de rattachement (porte **Écran de cible**), lisez la première phrase.
   → *Résultat attendu :* elle parle **du code**. Le QR n'est mentionné qu'**en dessous**, comme
   raccourci — « si l'appareil photo répond ». L'ordre inverse existait auparavant.

2. Regardez le pavé de touches sous le champ.
   → *Résultat attendu :* **32 touches**. Cherchez la lettre **O**, la lettre **I**, le chiffre **0**
   et le chiffre **1** : **aucun des quatre n'est proposé**. C'est normal — les codes n'en
   contiennent jamais, et pouvoir les taper ne menait qu'à un refus incompréhensible.

3. Touchez quelques touches, puis **← Corriger**, puis **Tout effacer**.
   → *Résultat attendu :* le code s'écrit en gros dans le champ, se corrige lettre à lettre, se vide.

4. Sur une tablette ou un téléphone, touchez le **champ** lui-même.
   → *Résultat attendu :* le clavier du système **ne s'ouvre pas**. Le pavé suffit ; deux claviers
   superposés cacheraient l'écran.

---

## Scénario 3 — L'administration : le déroulé d'abord, et un repère qui ne bouge pas (A02, A04)

1. Ouvrez la porte **Administration** et connectez-vous.
   → *Résultat attendu (A01) :* sous le formulaire, un lien **« ← Choisir un autre appareil »**. Il
   permet de ressortir si l'on s'est trompé de porte.

2. Une fois connecté, regardez l'ordre des trois axes.
   → *Résultat attendu :* **Pilotage** en premier, puis **Gestion**, puis **Atelier**. L'atelier
   venait en tête auparavant, sans raison métier.

3. Regardez la liste des tournois, en dessous.
   → *Résultat attendu :* l'ordre est **par état** — en cours, en pause, prêt, terminé, brouillon,
   archivé, annulé — puis **par date**. Un tournoi daté d'aujourd'hui porte la mention
   **« Aujourd'hui »**.

4. Si plusieurs états coexistent, une **rangée de filtres** apparaît au-dessus de la liste.
   → *Résultat attendu :* chaque filtre porte son décompte. Cliquer sur un ou plusieurs états
   restreint la liste ; **« Tous »** la rétablit. Si vous ne gardez que des états sans tournoi, un
   message le dit — la liste ne se vide pas en silence.

5. Entrez dans un tournoi (axe **Pilotage**), puis ouvrez plusieurs écrans à la suite.
   → *Résultat attendu :* un **bandeau** reste en haut de la zone de contenu, quel que soit l'écran :
   nom du tournoi, état, date et lieu, le **départ courant** (« Départ 2 · 14:00 — en cours »), et le
   fil « Pilotage › nom de l'écran ». Il **suit le défilement** : descendez dans un long tableau, il
   reste visible.

6. Passez dans l'axe **Gestion**.
   → *Résultat attendu :* le bandeau est toujours là, **sans le départ**. C'est voulu : une
   inscription ou un paiement ne se rattachent pas au créneau qui se tire à l'instant.

---

## Scénario 4 — De l'air (A02, A11)

1. Sur un écran large, ouvrez n'importe quel écran d'administration.
   → *Résultat attendu :* le contenu occupe **beaucoup plus de largeur** qu'avant. Les cartes et les
   tableaux ne sont plus tassés dans une colonne étroite au milieu de l'écran.

2. Ouvrez la même application sur un **téléphone**, porte **Public**.
   → *Résultat attendu :* la lecture reste **étroite et confortable**. Élargir un texte au-delà d'une
   soixantaine de caractères par ligne le rendrait moins lisible, pas plus.

---

## Scénario 5 — Les fenêtres de confirmation (A15)

1. Dans l'axe **Pilotage**, ouvrez **Feu vert** et, s'il y a des duels prêts, cliquez sur le bouton
   de lancement.
   → *Résultat attendu :* une **vraie fenêtre** s'ouvre au centre de l'écran, avec un titre
   (« Lancer le tour ? »), une phrase qui dit ce qui va se passer (« les postes de cible et les écrans
   de salle sont prévenus immédiatement »), le **détail chiffré** dans un cadre, et deux boutons :
   **Annuler** et **Lancer le tour**. Ce n'est plus la petite boîte grise du navigateur.

2. Appuyez sur la touche **Échap**.
   → *Résultat attendu :* la fenêtre se ferme, rien n'est lancé.

3. Faites de même sur d'autres gestes : **Terminer le tournoi** (écran Complétude), **Révoquer** un
   poste (Supervision), **Retirer** un écran de salle (Écrans de salle).
   → *Résultat attendu :* même type de fenêtre à chaque fois, avec un **filet rouge en haut** pour ce
   qui fige ou détruit, et un bouton de confirmation qui **répète le geste** (« Terminer »,
   « Révoquer », « Retirer l'écran ») — jamais un simple « OK ».

---

## Scénario 6 — La cible : le pavé s'appelle, les autres relisent (S02, S05)

1. Rattachez un appareil à une cible et attendez la grille des archers.
   → *Résultat attendu :* **aucun pavé n'est ouvert**. Sous la grille, une invite : *« Touchez un
   archer pour ouvrir le pavé de saisie. »* Auparavant le pavé s'ouvrait d'office sur le premier
   archer, ce qui recouvrait la grille et exposait à saisir pour quelqu'un qu'on n'avait pas choisi.

2. Touchez le nom d'un archer.
   → *Résultat attendu :* le pavé s'ouvre **pour lui**. Son en-tête affiche le **cumul de série** en
   plus du total de la volée, et un lien **Fermer**.

3. Touchez **le même nom** une seconde fois.
   → *Résultat attendu :* le pavé se referme et la grille complète réapparaît.

4. Regardez une ligne d'archer dans la grille.
   → *Résultat attendu :* sous son nom, une **bande de petites cases**, une par volée du barème :
   le **total** de chaque volée déjà saisie, un point pour celles qui restent, et un cadre vert pour
   celles que le scoreur a validées. C'est la contre-vérification : chaque archer relit ce qui a été
   tapé pour lui **sans toucher au pavé**.

5. Passez sur un **duel** (écran de saisie en duels), et regardez un camp.
   → *Résultat attendu :* le nom et le total sont sur une **première ligne**, les cases de flèches
   sur une **seconde**, larges, sur toute la largeur. Elles ne se partagent plus une rangée avec le
   nom — un nom long les écrasait.

6. Réduisez la fenêtre à la largeur d'un téléphone.
   → *Résultat attendu :* les touches de zones passent en **grille pleine largeur** et **grandissent**
   au lieu de rétrécir. L'indication « n/12 volées » disparaît — la bande de relecture la donne déjà.

---

## Scénario 7 — L'écran de salle (P06, P07)

1. Rattachez un appareil par la porte **Écran de salle**, sur un tournoi dont le tableau est lancé.
   → *Résultat attendu :* l'affichage occupe **tout l'écran**, sans en-tête d'application ni marges.
   Auparavant il tenait dans une colonne au milieu de l'écran.

2. Attendez que la vue **Affectations** passe dans le défilé.
   → *Résultat attendu :* elle affiche d'abord **« Tour en cours »** (le pas de tir, par cible), puis
   **« Tous les archers »** par nom, page par page — environ **20 secondes** par page.

3. Sur une page de noms, regardez les deux repères en haut.
   → *Résultat attendu :* à gauche, les **lettres couvertes** en gros (« DUP → LEF ») ; à droite, le
   **compteur de pages** (« 3/5 »), plus gros encore. Ce sont les deux seules choses qu'on lit du fond
   de la salle.

4. Faites imposer une vue depuis l'administration (Supervision → piloter les écrans).
   → *Résultat attendu :* l'écran affiche **« Vue imposée par l'organisation »**, mais **plus de compte
   à rebours**. Le décompte reste visible côté administration uniquement.

5. Approchez-vous de la machine et passez la souris en haut à droite de l'écran (ou appuyez sur Tab).
   → *Résultat attendu :* un bouton **« Décrocher cet écran »** apparaît. Il est **invisible au
   repos** — depuis la salle, il n'y a rien à voir.

---

## Scénario 8 — Le classement (A16)

1. Ouvrez **Classement en direct** (administration ou porte Public) sur un tournoi de plus de huit
   archers.
   → *Résultat attendu :* les **huit premiers** restent affichés en permanence ; le reste est dans un
   **cadre qui défile** sous eux, colonnes alignées avec celles du haut.

2. S'il existe deux archers **au même total dans la même catégorie**, regardez leurs lignes et le bas
   du tableau.
   → *Résultat attendu :* les lignes concernées portent un **filet ambre** à gauche, et une phrase
   apparaît sous le tableau : *« Ex æquo signalés : à total égal, le plus grand nombre de 10
   départage, puis le nombre de 9. »*

3. S'il n'y a **aucune** égalité, regardez le bas du tableau.
   → *Résultat attendu :* **la phrase n'est pas là**. Elle n'apparaît qu'au moment où elle s'applique.

---

## Scénario 9 — Imprimer d'avance (A08, A12)

1. Axe **Pilotage** → **Postes de cible**, sur un tournoi dont les codes sont préparés.
   → *Résultat attendu :* à côté de « Compléter les codes manquants », un bouton **« Imprimer toutes
   les étiquettes (PDF) »**. Cliquez : un PDF se télécharge, une page par cible (QR + code).

2. Axe **Pilotage** → **Scoreurs**, avec au moins un scoreur déclaré.
   → *Résultat attendu :* sous la liste, **« Imprimer toutes les cartes (PDF) »**. Cliquez : un PDF
   se télécharge, une page par scoreur (nom + code).

> À retenir : ces deux documents étaient **déjà produits par le serveur** depuis longtemps, mais
> aucun écran ne permettait de les demander.

3. Axe **Pilotage** → **Supervision**.
   → *Résultat attendu :* deux **bandeaux repliables** — « Écrans de cible » et « Écrans de salle » —
   chacun avec son compteur (« 28/30 en ligne »). Si des postes ne sont pas en ligne, le bandeau
   affiche **« ▲ 2 à vérifier »** et s'ouvre **de lui-même** ; sinon il est replié.

4. Repliez un bandeau qui porte une alerte.
   → *Résultat attendu :* l'alerte **reste lisible sur le bandeau fermé**. C'est le point : un bandeau
   fermé sur trois tablettes mortes ne doit pas ressembler à un bandeau fermé sur un parc intact.
