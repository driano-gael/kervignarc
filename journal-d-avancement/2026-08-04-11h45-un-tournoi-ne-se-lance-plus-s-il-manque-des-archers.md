# 04/08/2026 — Un tournoi ne se lance plus s'il manque des archers

**E05US021** — le contrôle d'effectif remonte du terrain vers la table de l'organisateur.

## Le problème

Un déroulé se compose des semaines à l'avance, pour un nombre d'archers **attendu**. S'il contient
une phase du genre « les rangs 33 et suivants », il lui faut au moins 34 archers classés pour avoir
deux tireurs à opposer.

Jusqu'ici, un tournoi de 28 inscrits avec ce déroulé démarrait **sans rien dire**. Le problème
n'apparaissait qu'en pleine compétition, sur une tablette, au moment de monter le tableau — quand il
n'était plus temps de changer de format.

## Ce qui change

L'application **déduit du déroulé lui-même** combien d'inscrits il faut au minimum. Ce chiffre n'est
pas saisi : il se lit dans les phases composées, donc il ne peut pas les contredire.

- **À la composition**, le format annonce son plancher : « ce déroulé demande au moins 34 inscrits ».
- **Sur l'écran du tournoi**, tant que le compte n'y est pas, un encart le rappelle en continu :
  « 28 inscrits / 34 requis », avec la phase en cause — sans avoir à cliquer sur quoi que ce soit.
- **Au clic sur « Démarrer »**, le lancement est refusé, avec le même chiffre et la même raison.

Un club peut aussi **exiger davantage** que le nécessaire technique — « pas de tournoi de ce type
sous 40 archers ». Jamais moins : un chiffre sous le plancher réel serait un mensonge, et le
problème reviendrait sur la tablette.

## Ce qu'il faut savoir

Le calcul ne couvre que les phases qui prélèvent dans la **qualification**. Ailleurs — « les rangs 33
et suivants *du tableau* », « les gagnants du tour 2 », « le reste » — un rang ne se traduit pas en
nombre d'inscrits, et annoncer un chiffre faux serait pire que ne rien annoncer. Ces cas restent
signalés, comme avant, quand on simule un effectif à l'écran de composition.

Un tournoi dont aucun déroulé n'est encore composé démarre normalement : tant que rien n'est décidé,
il n'y a rien à exiger.
