# 31 juillet 2026, 12h05 — Classer tout le monde, du premier au dernier

Jusqu'ici, un tableau de duels désignait quatre archers : le vainqueur, le finaliste, et les deux de
la petite finale. Tous les autres sortaient du tournoi sans rang. C'est fini : le moteur sait
désormais **classer les 120 archers de 1 à 120**, comme le fait le classeur que le club utilise
depuis des années.

## Ce qui change

**Personne n'est éliminé.** Quand un archer perd, il ne rentre pas chez lui : il redescend dans un
tableau qui joue les places qu'il peut encore atteindre. Perdre au premier tour d'un tableau de 120,
c'est basculer dans le groupe des places 65 à 120 ; y perdre encore, c'est descendre d'un cran de
plus — jusqu'à un dernier match qui départage deux places exactement. Chacun repart donc avec un
rang, et ce rang se mérite jusqu'au bout.

**Un format qui s'ajuste au nombre d'inscrits.** Un déroulé préparé pour 120 archers ne devenait
faux que le jour où il n'y en avait que 82. Une phase peut maintenant se peupler de « les rangs 33
**et suivants** » ou de « **le reste** » — ce qu'aucune autre n'a pris — au lieu d'une plage figée.
Le même format sert les deux éditions.

**Une phase peut être alimentée par plusieurs endroits.** Le besoin venait du classeur lui-même :
sa grande finale reçoit les vainqueurs des quarts **et** un repêché du tableau secondaire. Le
modèle sait désormais décrire ce genre de composition.

## Ce qui le prouve

Le classeur `Tableaux.xlsx` — un vrai tournoi à 120 archers, 484 matchs — est devenu un **test
automatique**. Le moteur rejoue le tournoi et l'on vérifie qu'il retombe exactement sur les
appariements du premier tour, sur les 8 exemptés, sur les 58 matchs qui décident les places 5 à 120,
et sur le classement complet. Ce contrôle tournera à chaque modification : si un jour le moteur
dérive, il le dira tout de suite.

*Une précision honnête : les places 1 à 5 du classeur ne sont pas décidées par des duels mais par une
« grande finale » d'un genre particulier, où huit archers tirent ensemble et où le plus faible sort à
chaque manche. Ce format-là n'est pas encore programmé — c'est la prochaine étape. La vérification
porte donc sur les places 5 à 120.*

## Pour l'organisateur, concrètement

Rien à réapprendre : les tournois déjà composés se déroulent exactement comme avant, avec leur
podium à quatre places. Ce qui change, c'est ce qui devient **possible** — et l'écran de composition
qui permettra de choisir « je classe le podium » ou « je classe tout le monde », phase par phase,
arrive avec la prochaine étape du chantier.
