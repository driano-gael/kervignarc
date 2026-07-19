# Journal d'avancement

Ce dossier raconte **ce qui a été construit dans l'application, session après session**, dans un
langage **volontairement non technique**. Il s'adresse à un lecteur qui n'écrit pas de code : un
membre du club, un responsable, ou simplement soi-même dans six mois pour se rappeler « où on en
était ».

Ce n'est **pas** de la documentation technique (celle-ci vit dans [`docs/`](../docs/), les
[`stories/`](../stories/) et les [`docs/adr/`](../docs/adr/)). Ici, on répond à une seule question :
**« qu'est-ce que le logiciel sait faire de plus qu'avant, et pourquoi c'est utile ? »**

## Comment c'est organisé

- **Un fichier par session de travail.** À chaque session où quelque chose est livré, un nouveau
  fichier est ajouté — on n'écrase jamais les anciens : le dossier est un **journal**, pas un état
  courant. Lus dans l'ordre, les fichiers racontent l'histoire du projet.
- **Le nom du fichier porte la date et l'heure**, au format `AAAA-MM-JJ-HHhMM-titre-court.md`
  (ex. `2026-07-20-00h12-etat-des-lieux.md`). Ce format se **trie tout seul** dans l'ordre
  chronologique : le plus récent est toujours en bas de la liste.
- **Le premier fichier** (`…-etat-des-lieux.md`) est un peu différent : il ne raconte pas *une*
  session mais dresse le **point de départ** — tout ce que l'application savait déjà faire au moment
  où le journal a été ouvert.

## Ce qu'on y met (et ce qu'on n'y met pas)

| On écrit | On évite |
|---|---|
| Ce qu'un utilisateur peut faire de nouveau | Le nom des fichiers de code, des classes, des fonctions |
| Pourquoi c'était utile / quel problème ça règle | Le jargon (« port », « adapter », « migration »…) sans traduction |
| Les limites connues, ce qui reste à faire | Les détails d'implémentation |
| Une image mentale simple de la fonctionnalité | Le diff, les commandes, les numéros de commit |

En cas de doute : **si un archer ou un bénévole du club ne comprendrait pas la phrase, elle est trop
technique.**
