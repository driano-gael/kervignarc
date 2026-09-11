# 11 septembre 2026, 19 h 25 — Annuler une validation, sans faire disparaître l'archer

## Ce qui est nouveau

Le scoreur a enfin **un écran pour valider la qualification**. Il faut le dire simplement : jusqu'à
aujourd'hui, cette fonction existait dans le serveur mais **aucun bouton ne l'appelait**. Le
téléphone du scoreur savait tout faire en duels, en poules, au système suisse et à la colline — mais
pas sur l'épreuve que tout le monde tire en premier.

Son espace porte désormais un panneau **« Validation — qualification »** : il choisit un départ, un
archer, lit ses volées, et valide.

Et il peut **annuler une validation**. C'est ce que vous aviez demandé au questionnaire des
maquettes : *« plus de modification une fois validé »* d'un côté, *« une validation peut être
annulée, par admin et scoreur »* de l'autre. Ce ne sont pas deux règles qui se contredisent, c'est
**une procédure en deux temps** : on n'édite pas un score signé, on annule la signature, la cible
ressaisit, le scoreur revalide.

## Ce que ça change

- **L'erreur se répare là où elle a été faite.** Annuler rend la volée à la **tablette de la cible**,
  qui la ressaisit elle-même — au lieu que le scoreur corrige à sa place, sans que la cible le sache.
- **Annuler porte sur le bloc, pas sur une volée isolée.** Si vous validez toutes les deux volées,
  annuler l'une rouvre les deux : on ne laisse pas un trou au milieu d'un bloc signé.
- **La fenêtre de confirmation dit ce qu'elle va faire** : elle **nomme** les volées qui redeviennent
  saisissables, au lieu d'un « êtes-vous sûr ? » qui n'apprend rien.

## La décision qui a demandé un arbitrage

Pendant qu'une volée est rouverte, **que devient son score au classement** ?

Deux réponses se présentaient, et vous les avez **toutes les deux écartées**. Faire sortir la volée
des totaux le temps de la correction était le plus simple — mais alors, une annulation que personne
ne corrige (le scoreur annule, part en pause, l'affaire s'oublie) laissait cet archer **hors du
classement indéfiniment**, sans que rien ne le signale. Forcer l'annulation et la ressaisie en un
seul geste évitait le problème — mais interdisait justement de rendre la main à la tablette, qui est
tout l'intérêt de la manœuvre.

La voie retenue est la troisième : **le score reste compté pendant toute la correction.** Le
classement, le palmarès et l'écran de salle continuent d'afficher le total tel qu'il était, jusqu'à
la ressaisie. Ce qui se rouvre, c'est le **droit d'écrire**, pas le **compte**.

La contrepartie est assumée : le classement affiche un moment un score dont le scoreur sait déjà
qu'il est faux. C'est pourquoi la volée porte la mention **« En correction »** — elle n'est pas
décorative, elle est la moitié de la décision.

## Ce que l'arbitrage a sauvé sans qu'on le voie

Trois garde-fous se seraient relâchés en silence si la volée avait quitté les totaux : l'avertissement
quand on change la catégorie d'un archer **qui a déjà tiré**, le décompte « cibles avec scores »
qu'on lit avant de régénérer un plan de cibles, et la clôture d'un créneau. Les trois lisent la même
mesure. Avec la solution retenue, aucun ne bouge — et **un test par garde** le vérifie désormais,
au niveau où la garde vit, pas seulement au niveau de la mesure dont elle dérive.

## Ce qui ne change pas

- La **correction directe** d'une volée validée reste possible : les deux chemins coexistent.
- Les **duels**, le **Big Shoot Off** et les **barrages de places** ne sont pas touchés. Ils sont
  déjà réglés, chacun à sa façon — et pour le barrage, rouvrir sur saisie est une **décision**, pas
  un oubli : la refermer réintroduirait un défaut corrigé.

## Deux points trouvés par la relecture

La relecture croisée a rattrapé deux choses que l'implémentation avait manquées, et qui valent
d'être dites parce qu'elles portent sur le résultat, pas sur la forme.

**L'affichage public se contredisait.** Le suivi en ligne marquait « en attente » des volées dont
les points étaient déjà dans le total affiché juste au-dessus : un spectateur qui additionnait la
colonne obtenait zéro en face d'un total de 54. Corrigé — ce qui compte est publié comme comptant.

**Annuler pendant une pause menait dans une impasse.** L'annulation était permise, mais la
ressaisie et la revalidation, elles, sont gelées tant que la salle est en pause : la volée restait
donc ouverte sans aucun moyen de la refermer avant la relance. L'annulation est désormais refusée
pendant une pause — on y répare par la correction directe, comme avant.

## Un point à connaître

L'administrateur peut **annuler**, mais la **validation** reste réservée au scoreur. Après une
annulation par l'administrateur, c'est donc un scoreur qui revalide. Rien n'est bloqué entre-temps,
puisque le score reste compté — mais l'ouvrir aussi à l'administrateur demanderait une décision que
le questionnaire n'a pas prise.

Recette détaillée : [`docs/fonctionnel/E16US019.md`](../docs/fonctionnel/E16US019.md).
