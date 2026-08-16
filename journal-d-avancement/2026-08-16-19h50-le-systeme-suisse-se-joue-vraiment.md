# 16 août 2026, 19 h 50 — le système suisse se joue vraiment

Hier, l'application savait *dérouler* un système suisse : apparier les rondes, classer, dire à chaque
archer où il tire, publier le palmarès. Mais aucun écran ne permettait de le régler ni d'y saisir un
score — un format que la machine connaissait et que personne ne pouvait jouer. C'est réglé.

## Ce qui est nouveau

**On règle une phase au système suisse**, en choisissant simplement son nombre de rondes. L'écran
annonce en clair **combien de rondes l'effectif du jour autorise** : à effectif pair, on peut jouer
*n-1* rondes, à effectif impair *n*, au-delà desquelles deux archers se rencontreraient deux fois.
Cette limite existait déjà dans le moteur, mais elle ne se voyait nulle part : l'organisateur se
faisait refuser son étape sans comprendre pourquoi, ou voyait le jour J moins de rondes qu'il n'en
avait prévues, sans le moindre message.

**Le scoreur saisit ronde par ronde**, avec le même pavé que pour un duel ordinaire — c'en est un.
La ronde suivante n'apparaît qu'une fois la précédente entièrement saisie et validée, et **l'écran
dit pourquoi** : dans ce format, les adversaires se choisissent au classement du moment, donc ils ne
peuvent pas être connus d'avance. Sans cette phrase, il ne restait qu'une absence inexplicable.

**Le classement se lit entre les rondes** — rang, points, et le « Buchholz » qui départage à points
égaux en regardant la force des adversaires rencontrés. C'est la seule lecture d'avancement possible
d'un format sans arbre : personne n'y est éliminé, donc rien d'autre ne dit qui mène.

**L'organisateur pose les cibles** d'un clic, comme pour les poules.

## Un défaut ancien refermé au passage

L'espace scoreur affichait **un sélecteur de créneau par panneau de saisie** — trois hier, quatre
avec le suisse. Ils étaient indépendants : on pouvait changer de départ dans un panneau, saisir dans
un autre, et scorer les rencontres du mauvais créneau. Avec des identifiants parfaitement valides,
donc **sans le moindre message d'erreur**. Il n'y a désormais qu'un seul choix de départ, en tête
d'écran, et les quatre panneaux le suivent.

Dans le même esprit, le panneau « où je tire ensuite » distingue maintenant trois situations au lieu
de deux : *il a fini*, *il attend la ronde suivante* (l'archer au repos, ou celui dont la rencontre
vient d'être validée), et *on ne sait pas où il tire*. Les deux premières étaient confondues — et
l'on ne dit pas « c'est terminé » à quelqu'un qui a encore trois rondes à tirer : il range son arc.

## Ce qui reste à venir

Le **public** ne voit pas encore le détail des rondes. C'est un manque commun aux trois formats sans
arbre — les poules et la finale spectacle non plus n'y sont pas —, et il sera traité d'un bloc plutôt
que format par format.

Le passage à la ronde suivante est **automatique** dès que la précédente est close. Donner à
l'organisateur la main sur ce moment est à l'étude : cela demande de revoir une décision technique
prise avec le moteur, et cela mérite d'être instruit plutôt que bricolé.
