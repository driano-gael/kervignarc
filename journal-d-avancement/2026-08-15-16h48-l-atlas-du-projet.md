# 15 août 2026, 16 h 48 — l'atlas : ce qui fait règle, et depuis quand

**US : E00US018** · [ADR-0086](../docs/adr/0086-un-atlas-genere-le-depot-cartographie-sans-dependance.md)

## Ce qui ne marchait pas

Le projet écrit tout : 29 règles de travail, 83 décisions d'architecture, un registre de dette, un
suivi des US. Tout est versionné, rien n'est consultable d'un coup d'œil. La demande était celle-ci :
*« j'ai du mal à suivre les règles qui sont édictées, si elles sont toujours d'actualité, si elles
évoluent, du coup je ne vois pas bien l'état réel du projet, et son historique. »*

En regardant les chiffres, on comprend pourquoi la question n'avait pas de réponse : **82 décisions
sur 83 portent la mention « Accepté »**, et **une seule** est marquée « remplacée ». Le statut ne
distingue donc rien. En réalité **19 décisions ont été amendées** par une décision plus récente — et
cela n'est écrit **sur aucune des deux fiches concernées**. Celui qui ouvrait une décision y lisait
« Accepté » sans jamais apprendre qu'elle avait bougé depuis.

## Ce qui change

Un dossier `atlas/` qu'on **ouvre d'un double-clic**, sans rien lancer, sans internet.

- **Le règlement du jour.** Les règles en vigueur, dans l'ordre où elles sont écrites, lisibles
  d'une traite — sans historique qui encombre la lecture. C'est la « notice de jeu » demandée.
- **L'histoire de chaque règle.** Un clic sur une règle ouvre sa fiche : son texte actuel, puis
  chaque changement **daté**, avec son motif, l'US et la décision qui l'ont provoqué. L'histoire
  n'est pas ressaisie à la main — elle est lue dans l'historique du dépôt.
- **Les décisions, avec ce qui les a dépassées.** Chaque décision affiche noir sur blanc ce qui
  l'amende, et les « chaînes d'amendement » racontent une même question tranchée plusieurs fois.
- **L'écrit confronté au code.** Vingt-cinq décisions promettent de nommer les modules qui les
  appliquent — 90 modules et 234 fonctions ou classes. L'atlas vérifie que ces promesses tiennent
  encore. Il retrouve du premier coup un cas déjà signalé : une décision qui annonce une classe
  `Equipe` qui n'a jamais été écrite.
- **Une recherche** sur l'ensemble, expressions exactes comprises.

## Ce qu'il a trouvé dès le premier jour

Onze décisions sur quatre-vingt-trois sont datées au format français quand tout le reste du registre
utilise le format international. Aucune conséquence pratique, mais c'est le genre de dérive
silencieuse que personne ne voit en relisant un fichier à la fois.

## Ce qu'il ne dira jamais

Il ne dit **pas** si une règle est encore d'actualité : cela ne se décide pas mécaniquement. Il
affiche des **signaux à vérifier**, jamais un verdict. Et quand il contrôle qu'une décision est bien
portée par un module, il vérifie que le fichier **existe** — pas qu'il **fait** ce qui était promis.

## Ce qui garantit qu'il reste vrai

C'est le point qui distingue cet atlas d'une documentation parallèle, qui se serait périmée en trois
semaines : il est **entièrement regénéré depuis les fichiers du projet**, et la vérification
automatique du dépôt **échoue** si ce qui est affiché ne correspond plus aux sources. Il n'ajoute
aucune tâche : personne n'a rien à tenir à jour à la main.

Il n'ajoute pas non plus la moindre bibliothèque extérieure — ce qui est vérifié, là encore,
automatiquement.

## Ce qui reste à faire

L'atlas ne couvre aujourd'hui que les **règles et les décisions**. Quatre tranches sont prévues, à
prendre quand vous le déciderez : l'**avancement** (US, epics, dette), la **carte du code**, le
**modèle métier** (cycles de vie, entités), et les **flux** (de la saisie d'une flèche jusqu'à
l'affichage sur les tablettes).

## À vérifier

Ouvrir `atlas/index.html` d'un double-clic, cliquer une règle pour voir son histoire, puis passer
aux décisions et ouvrir `ADR-0075` : elle doit annoncer qu'elle est **partiellement dépassée**. La
page « Écarts constatés » liste ce que l'atlas a trouvé. La checklist de vérification à l'écran
(dont les petits écrans) est dans [`atlas/README.md`](../atlas/README.md).
