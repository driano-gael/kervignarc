# 31 juillet 2026, 14h58 — Tous les formats du club, enfin nommables

Le logiciel savait composer trois choses : une qualification, un tableau à élimination directe, un
tableau de placement. Un tournoi réel en compte bien davantage — l'échauffement du matin, le barrage
qui départage les ex æquo, les poules, la grande finale spectacle. Tout cela devait être approché
avec les briques disponibles, ou tenu à la main sur une feuille à côté.

Ce n'était pas une question de programmation : **les règles de ces formats n'étaient écrites nulle
part**. Elles ont été fournies ce matin. Le catalogue est donc passé de trois formats à douze d'un
seul coup.

## Ce qui est nouveau à l'écran

Sur l'écran **Phases**, la liste des formats proposés s'allonge, et chacun affiche désormais sous le
menu une phrase qui dit ce qu'il fait — sans quoi « Colline » ou « Système suisse » ne renseignent
personne :

- **Échauffement** — sans point ni classement : il occupe du temps et des cibles, et c'est tout ce
  qu'on lui demande.
- **Barrage** — départage les archers à égalité, à une flèche, avant de monter un tableau.
- **Poules** — des groupes qui se rencontrent entre eux ; le classement de poule désigne les
  qualifiés.
- **Big Shoot Off** — la grande finale : plusieurs archers tirent ensemble et le plus faible sort à
  chaque manche, jusqu'au vainqueur.
- **Système suisse** — des rondes où les vainqueurs affrontent les vainqueurs ; personne n'est
  éliminé, et le classement se précise ronde après ronde.
- **Colline** — des défis entre voisins de classement : le gagnant monte, le perdant descend.

## La question qui bloquait le projet depuis le début est fermée

Le **Big Shoot Off** figurait au cahier des charges depuis l'origine sans que personne ne sache
exactement ce que c'était — au point que le document hésitait lui-même à le ranger parmi les
« façons de compter les points » ou parmi les « formats de tournoi ». La règle donnée ce matin
tranche : c'est un **format**, et le « Big » désigne le **nombre d'archers**, pas le nombre de
flèches.

C'est aussi ce qui manquait pour boucler la vérification faite ce midi sur le classeur du club : les
places 1 à 5 y sont décidées par une grande finale de ce type, que le logiciel ne savait pas encore
décrire. Il le sait maintenant.

## Trois formats étaient déjà là sans qu'on le sache

En écrivant les règles, il est apparu que trois des formats attendus n'étaient pas des formats du
tout, mais des **réglages** de ce qui existait déjà :

- le **repêchage** est une façon de dire où va un perdant — il ressort du tableau au lieu d'y prendre
  un rang, et une phase suivante le récupère ;
- le **handicap** est une façon de compter les points : score réalisé **plus** le handicap de
  l'archer ;
- la **finale spectacle** est un tableau à huit avec petite finale, plus le barème de duel déjà
  disponible. Ce qui fait vraiment sa différence — musique, écran géant, commentateur, compte à
  rebours — relève de l'écran de salle, pas du déroulé.

Les distinguer a évité de programmer trois fois la même chose sous trois noms.

## Le handicap, et une limite qu'il faut dire

Chaque archer peut porter deux valeurs, saisissables sur l'écran des archers : un handicap
**officiel**, celui que le club entretient, et une **surcharge** ponctuelle qui le remplace pour un
tournoi donné — utile quand la valeur de référence est visiblement dépassée (un jeune qui progresse
vite, un archer qui reprend après une longue absence) sans qu'on veuille pour autant réécrire la
fiche du club. La valeur retenue s'affiche sur la ligne de l'archer, avec un astérisque quand c'est
une surcharge.

⚠️ **Le logiciel ne fournit aucune table de handicap, et ce n'est pas un oubli.** La fédération
française n'a pas de système de handicap officiel ; celui qui fait référence est anglo-saxon. En
reconstituer un aurait produit des classements qui *ont l'air* justes et qui sont faux — le plus
dangereux des défauts, puisqu'il ne se remarque pas. C'est donc le club qui saisit les valeurs et qui
en répond.

## Où l'on en est, et ce qui vient ensuite

Cette étape livre les **formats** et de quoi les **assembler** dans un déroulé. Les faire tourner le
jour du tournoi — remplir automatiquement une phase depuis la précédente, enchaîner les manches d'un
Big Shoot Off, afficher un classement de poule en direct — est l'objet des deux étapes suivantes du
chantier : composer et simuler un déroulé, puis voir le tournoi se dérouler.

Quelques choix ont dû être faits faute de précision dans les règles (le barème des poules, le nombre
de rondes du système suisse, ce qui se passe entre deux manches d'un Big Shoot Off). Ils sont tous
**modifiables par réglage** et listés dans le scénario de recette : il suffit de dire lesquels
changer. Deux points méritent un regard particulier, tous deux sur le Ladder : l'exemple chiffré
donné avec sa règle ne correspond pas à la règle elle-même (nous avons appliqué **la règle**), et
« défier le 5 **ou** le 4 » a été traduit en faisant alterner la distance des défis d'une manche à
l'autre — sans quoi le classement ne se remettrait jamais à l'endroit.
