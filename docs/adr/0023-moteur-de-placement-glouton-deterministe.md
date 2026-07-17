# ADR-0023 — Moteur de placement : glouton déterministe, contraintes câblées, recalcul à la demande

- **Statut** : Accepté
- **Date** : 2026-07-17
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E03-placement.md`](../../stories/E03-placement.md) (E03US001) ;
  [`docs/glossaire.md`](../glossaire.md) (`Plan de cibles`, `Conflit de placement`)
- **Introduit par** : E03US001 (moteur de placement `domain/placement.py`).
- **Voisin** : [ADR-0004](0004-format-de-tournoi-comme-configuration.md) formalise l'**autre** moteur
  (celui des phases, politiques injectables) ; celui-ci relève d'un régime différent, explicité au
  point 2. S'appuie sur [ADR-0022](0022-hauteur-de-centre-sur-la-categorie.md) pour la contrainte de
  hauteur.

## Contexte et problème

E03US001 introduit la première brique d'EPIC-03 : répartir les archers d'un départ sur les cibles
d'un gabarit. C'est une **décision structurante fondatrice** — plusieurs US en dépendent (E03US004
ajustement manuel, E03US006 mixité club, E03US007 séparation catégorie, E07 vue publique, E09
exports). Trois choix la structurent, aucun trivial, et le CA ne les impose pas :

1. **Quel algorithme** ? Le placement sous contraintes (espace, positions, partage de carton,
   hauteur) est un problème de bin-packing — NP-difficile dans le cas général. Faut-il viser
   l'**optimum** (retour arrière, recherche) ou un **glouton** ?
2. **Les contraintes sont-elles des stratégies injectables** (comme les politiques du moteur de
   phases, règle 2) ou **câblées** dans le moteur ?
3. **Le plan est-il persisté** ou **recalculé à la demande** ?

## Décision

**1. Glouton déterministe, mono-passe, sans retour arrière.** Les archers sont triés par
`(hauteur, blason, id)` — ce qui rend contigus les tireurs d'une même hauteur puis d'un même blason —
et l'on remplit cible par cible, en passant à la suivante dès qu'un archer n'entre plus. Un archer
qui n'entre sur **aucune** cible restante ressort en **conflit** (`NON_PLACE`), jamais en échec
silencieux. Propriétés retenues, dans l'ordre :

- **Déterminisme** avant optimalité. Le jour J, un placement **reproductible et explicable** (« cet
  archer est ici parce que sa butte est à sa hauteur, les autres étaient pleines ») vaut mieux qu'un
  optimum opaque que l'organisateur ne peut pas justifier à un club. C'est aussi une exigence de test
  (règle 9 : pas d'aléa).
- **Sous-optimalité assumée.** Le glouton peut laisser de l'espace perdu sur une cible plutôt que de
  revenir en arrière. Ce n'est **pas** une incorrection (un archer n'est jamais mis en conflit alors
  qu'une place existait : les archers restants, de blason `id` supérieur, ne peuvent pas réutiliser
  l'espace abandonné) — c'est du gaspillage. Il est rattrapé par l'**ajustement manuel** (E03US004),
  dont il **motive l'existence** : un mono-club le jour J préfère un auto-placement instantané qu'il
  retouche à la marge à un solveur qui rend un plan parfait mais fige tout.
- Option **optimale / retour arrière écartée** : coût d'implémentation et de test sans commune mesure
  avec le besoin (≤ quelques dizaines de cibles), et l'ajustement manuel est de toute façon requis
  pour les cas humains que nulle contrainte n'exprime (deux frères sur la même butte, etc.).

**2. Contraintes câblées dans le moteur — pas des stratégies injectables.** La règle 2 impose
l'injection pour les **politiques du moteur de tournoi** (`routing`, `scoring`, `seeding`, `byes`,
`tiebreak`, `depth`) : ce sont des axes où **les formats FFTA diffèrent**, donc de la configuration.
Les contraintes de placement (espace, positions, partage, hauteur) ne sont **pas** de cette famille :
elles découlent de la **physique de la salle**, identique quel que soit le format. Les câbler dans
`_CibleEnCours.accueille` est donc correct, pas un raccourci. Le jour où une **3ᵉ** contrainte réelle
s'ajoutera (E03US006 mixité, E03US007 catégorie) **et** qu'une duplication apparaîtra, on extraira un
mécanisme de contraintes — **sur preuve, pas par anticipation** (règle « 3ᵉ occurrence » du § Dette).
Introduire des « stratégies de contraintes injectables » dès la 1ʳᵉ serait de la sur-ingénierie.

**3. Recalcul à la demande, sans persistance.** `ServicePlacement.plan_de_cibles` recalcule le plan
à chaque lecture depuis les inscriptions courantes ; aucune entité de plan n'est persistée en
E03US001. Motif : tant que le plan n'est pas **ajustable** (E03US004), le persister n'apporte rien
qu'un risque de désynchronisation avec les inscriptions (un archer ajouté après coup n'apparaîtrait
pas). La persistance naît avec l'ajustement (E03US004 : la file d'écriture porte les déplacements
manuels), pas avant. Le périmètre d'E03US001 est donc **domaine + service + endpoint de lecture**.

## Conséquences

- **+** Placement **reproductible, testable, explicable** ; le moteur pur (`domain/placement.py`) se
  teste sans base ni framework, depuis le CA.
- **+** La physique de la salle est au bon endroit (domaine), le format reste ailleurs (politiques
  injectables) : les deux régimes ne se contaminent pas.
- **−** Plan **sous-optimal** possible (espace perdu) — contrepartie assumée, adressée par l'ajustement
  manuel E03US004. À ne pas confondre avec une incorrection : le rapport de conflits ne ment pas.
- **−** L'endpoint **recalcule** à chaque appel (glouton sur tous les inscrits d'un départ) ; sur le
  LAN mono-club (≤ quelques centaines d'archers, ≤ quelques dizaines de cibles) c'est négligeable. Si
  une US future en fait un point chaud, la persistance d'E03US004 le résout en cache naturel.
- **−** Ajouter une contrainte avant la 3ᵉ occurrence tenterait de généraliser trop tôt : la décision
  câble **volontairement**, et documente le seuil d'extraction.
