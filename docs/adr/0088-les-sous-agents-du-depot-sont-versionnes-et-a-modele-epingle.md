# ADR-0088 — Les sous-agents du dépôt sont versionnés et à modèle épinglé

- **Statut** : Accepté
- **Date** : 2026-08-16
- **Décideurs** : Organisateur / Architecte

## Contexte et problème

`CLAUDE.md` § Économie de contexte pose depuis longtemps la bonne règle : « la localisation part à
un sous-agent […] les fichiers atterrissent dans *son* contexte, l'assistant ne reçoit que la
conclusion. Un sous-agent qui **localise** peut tourner sur un modèle moins cher ; un sous-agent qui
**juge** garde le modèle fort. »

Trois choses lui manquaient pour être appliquée de façon fiable.

**1. Le modèle était hérité, donc volatil.** Un sous-agent sans définition propre tourne sur le
modèle de la session. Conséquence dans les deux sens : une exploration lancée depuis une session
Opus coûtait le prix fort pour un travail sans jugement ; et — plus grave — un `/model sonnet`
choisi pour une US mécanique dégradait **la revue** au « lance la PR » suivant, sans qu'aucun signal
ne le dise. La barrière qualité que `CLAUDE.md` déclare non optimisable l'était donc en pratique,
par accident.

**2. « Peut tourner sur un modèle moins cher » est une permission, pas une pratique.** Elle suppose
que l'assistant y pense à chaque appel, dans une session dont le contexte a pu être compacté depuis.
Une permission qu'il faut se rappeler d'exercer n'est pas un mécanisme.

**3. Le savoir-faire de la localisation n'était écrit nulle part.** Chercher `ServiceSaisie` et non
`ScoringService`, `Depart` et non `Session` ; ne pas proposer `prototype/` comme réponse ; lire
`docs/dette.md` par sa table et non en entier ; chercher une **seconde** occurrence avant de
conclure. Ce savoir était re-transmis à la main, ou perdu.

Le déclencheur immédiat est ADR-0013 décision 8, qui a versionné les six agents de la revue. Le
septième — `localiser` — a été livré dans le même lot **sans être nommé nulle part** : ni à l'ADR,
ni aux corps de commit, ni à la table de portage. La revue l'a relevé et a refusé de trancher seule,
au motif que la décision déborde `/revue-us` : elle vaut pour **tout** sous-agent du dépôt, présent
et futur. D'où cet ADR.

## Options envisagées

- **Rien — garder la permission de `CLAUDE.md`.** Défendable : zéro fichier, zéro maintenance.
  Écartée pour la raison 1 — elle laisse la barrière qualité de la revue dépendre du modèle de
  session, ce que `CLAUDE.md` interdit par ailleurs.
- **Épingler dans la commande plutôt que dans un agent.** Écartée : une commande ne s'applique qu'à
  son propre déroulé. Une exploration lancée hors `/revue-us` — c'est-à-dire la majorité — n'en
  bénéficierait pas.
- **Un agent versionné par rôle, modèle épinglé au frontmatter** — retenue.

## Décision

**1. Tout sous-agent réutilisable du dépôt est un fichier versionné de `.claude/agents/`.** Il
voyage entre les postes, il se relit, il se diffe, il passe en revue comme le reste du code. Un
sous-agent défini à la volée dans un prompt n'est pas reproductible et n'a pas de mémoire d'un poste
à l'autre.

**2. Son modèle est épinglé au frontmatter, jamais hérité.** Le critère est celui de `CLAUDE.md` :

| Ce que fait l'agent | Modèle | Pourquoi |
|---|---|---|
| **Juger** — les cinq relecteurs de `/revue-us` | `opus` | Barrière qualité. Elle ne s'optimise pas (ADR-0013) |
| **Localiser** — `localiser` | `sonnet` | Beaucoup d'entrée, peu de jugement. Pas `haiku` : 200 K de contexte, et ce dépôt peut le saturer — une localisation tronquée est fausse **et** plausible, le pire mode de défaillance pour un agent dont la sortie sert de base à l'implémentation |
| **Exécuter et recopier** — `porte-mecanique` | `haiku` | Aucun jugement : lit `ci.yml`, lance, rend les codes de sortie et les échecs verbatim |

**3. Épingler, c'est aussi retirer un choix.** `CLAUDE.md` *permettait* un modèle moins cher pour la
localisation ; cet ADR l'**impose**. C'est le prix de la fiabilité, et il se paie dans les deux sens :
une exploration réellement difficile ne montera pas d'elle-même en Opus. Le recours reste ouvert —
l'appelant peut passer un `model` explicite à l'appel — mais il devient un geste conscient au lieu
d'un défaut silencieux.

**4. Les outils sont restreints au rôle.** `localiser` n'a ni `Edit` ni `Write` : il ne modifie rien.
Même réserve qu'à ADR-0013 décision 8 — `Bash` reste ouvert pour `git log`/`git grep`, donc
l'interdiction d'écrire y demeure pour partie une consigne.

**5. La description du frontmatter est prescriptive.** C'est elle, et non le corps du fichier, que
l'orchestrateur lit pour choisir. Elle dit **quand** appeler l'agent et **quand ne pas** l'appeler.

## Conséquences

- **+** La barrière qualité de la revue ne peut plus se dégrader en silence quand la session change
  de modèle. C'est l'effet principal, et il vaut à lui seul l'ADR.
- **+** Le savoir-faire de localisation propre à ce dépôt (vocabulaire FFTA, `prototype/` non
  citable, documents lourds lus par section, seconde occurrence à chercher) est écrit une fois et
  s'applique à chaque appel.
- **+** L'économie de contexte devient structurelle et non plus disciplinaire : la sortie volumineuse
  reste chez l'agent, quel que soit l'état de la session appelante.
- **−** Un fichier de plus à maintenir par rôle, et un modèle figé qui peut être le mauvais choix sur
  un cas atypique (cf. décision 3).
- **−** **Un frontmatter mal formé rend l'agent introuvable sans message d'erreur.** Le risque est
  réel : `localiser.md` a été livré avec un `:` non échappé dans sa `description`, qu'un parseur YAML
  strict refuse — le harnais l'a accepté, mais dépendre d'une tolérance non documentée est fragile.
  Couvert depuis par `backend/tests/test_agents_de_revue.py`, qui vérifie l'existence et le
  frontmatter des agents cités par `/revue-us`. **`localiser` n'y est pas couvert** : il n'est cité
  par aucune commande, donc rien ne prouve qu'il se charge. Résidu assumé.
- **−** Le critère du tableau (juger / localiser / exécuter) est un **jugement**, pas une mesure.
  Aucune donnée du projet ne démontre que Sonnet suffit à la localisation ; c'est un pari, à réviser
  si une exploration rend une conclusion fausse.
- **−** ⚠️ **Un agent versionné n'est pas un agent à effet immédiat.** Le registre est **figé au
  démarrage de la session** (vérifié deux fois le 17/08/2026 : un agent neuf reste introuvable, un
  `tools:` modifié n'est pas relu). Corriger un agent, c'est donc corriger *la session suivante* —
  jamais celle en cours. Deux corollaires : une correction d'agent ne peut pas être éprouvée dans le
  commit qui l'écrit, et un fichier d'agent poussé sur `main` n'agit chez les autres postes qu'à leur
  prochain démarrage. Ce n'est pas un défaut du dépôt, c'est une propriété du harnais — mais elle doit
  être connue, sans quoi on croit avoir corrigé ce qu'on n'a fait qu'écrire.
- **−** `Bash` reste non scopé sur tous les agents, y compris ceux qui n'ont aucun besoin d'écrire :
  la restriction d'outils est donc partielle. Le trou est constaté, pas théorique
  (**[DETTE-069](../dette.md)**, incident `e8d3258`), et sa résorption dépend d'une question ouverte
  — le champ `tools:` accepte-t-il et applique-t-il un spécificateur `Bash(git log:*)` ? — que le
  point précédent empêche de trancher dans la session qui la pose.

## Porté dans le code par

| Ce qui applique la décision | Décisions portées |
|---|---|
| [`.claude/agents/localiser.md`](../../.claude/agents/localiser.md) | 1, 2 (`model: sonnet`), 3, 4, 5 — et le savoir-faire de localisation propre au dépôt |
| [`.claude/agents/porte-mecanique.md`](../../.claude/agents/porte-mecanique.md) | 1, 2 (`model: haiku`), 5 |
| [`.claude/agents/revue-axe-a.md`](../../.claude/agents/revue-axe-a.md) · [`-b`](../../.claude/agents/revue-axe-b.md) · [`-c1`](../../.claude/agents/revue-axe-c1.md) · [`-c2`](../../.claude/agents/revue-axe-c2.md) · [`-d`](../../.claude/agents/revue-axe-d.md) | 1, 2 (`model: opus`), 4 — cas d'application ; leur conduite relève d'[ADR-0013](0013-conduite-de-la-revue-d-us.md) |
| [`backend/tests/test_agents_de_revue.py`](../../backend/tests/test_agents_de_revue.py) | 2 et 4 — transforme l'épinglage et le retrait d'`Edit`/`Write` en preuve machine |

⚠️ Comme pour ADR-0013, ces chemins sont **hors du périmètre de l'atlas** (`_RACINES_DE_CODE` ne
contient pas `.claude/`) : le contrôle `portage-inexistant` ne les confronte pas au dépôt. Voir
[DETTE-068](../dette.md).

## Liens

`CLAUDE.md` § Économie de contexte (« déléguer la lecture, garder le jugement ») ·
[ADR-0013](0013-conduite-de-la-revue-d-us.md) (conduite de la revue — cas d'application) ·
[ADR-0086](0086-un-atlas-genere-le-depot-cartographie-sans-dependance.md) (stdlib pure) ·
[DETTE-068](../dette.md).
