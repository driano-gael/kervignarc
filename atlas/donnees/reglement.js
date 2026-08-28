/* GÉNÉRÉ par `cd backend && python -m atlas` — ne pas éditer à la main.
   Toute modification sera écrasée à la régénération et rejetée par la CI. */
window.ATLAS = window.ATLAS || {};
window.ATLAS.reglement = {
 "regles": [
  {
   "adr": [],
   "amendements": [],
   "corps": "`backend/domain/` n'importe **aucun** framework (FastAPI, SQLAlchemy,\n   Pydantic) ni aucune autre couche (`api/`, `application/`, `infrastructure/`, `bootstrap/`). Pur et\n   synchrone. Vérifié par `backend/tests/test_domain_isolation.py` (AST) en pre-commit et en CI.",
   "fichier": "CLAUDE.md",
   "identifiant": "isolation-du-domaine",
   "ligne": 78,
   "ligne_fin": 80,
   "rang": 1,
   "section": "Règles non négociables",
   "titre": "Isolation du domaine",
   "us": []
  },
  {
   "adr": [],
   "amendements": [],
   "corps": "Tout pointe vers le domaine. Les ports (interfaces) vivent dans le\n   domaine, les adapters dans `infrastructure/`. Les politiques du moteur (`routing`, `scoring`,\n   `seeding`, `byes`, `tiebreak`, `depth`) sont des stratégies injectables — un format de tournoi est\n   de la **configuration**, pas du code.",
   "fichier": "CLAUDE.md",
   "identifiant": "sens-des-dependances",
   "ligne": 81,
   "ligne_fin": 84,
   "rang": 2,
   "section": "Règles non négociables",
   "titre": "Sens des dépendances",
   "us": []
  },
  {
   "adr": [],
   "amendements": [],
   "corps": "Métier en **français FFTA** (`Archer`, `Cible`, `Blason`, `Volee`, `Fleche`,\n   `Duel`, `Depart`, `Categorie`, `Phase`), technique en **anglais** (`Repository`, `Adapter`,\n   `Service`, `Router`, `Store`). Cohérent entre code, API, UI et doc — voir\n   [`docs/glossaire.md`](docs/glossaire.md).",
   "fichier": "CLAUDE.md",
   "identifiant": "vocabulaire",
   "ligne": 85,
   "ligne_fin": 88,
   "rang": 3,
   "section": "Règles non négociables",
   "titre": "Vocabulaire",
   "us": []
  },
  {
   "adr": [],
   "amendements": [],
   "corps": "mypy strict côté Python (pas d'`Any` implicite), TS `strict` (pas d'`any` non\n   justifié). Immutabilité privilégiée dans le domaine (dataclasses `frozen`).",
   "fichier": "CLAUDE.md",
   "identifiant": "typage-strict",
   "ligne": 89,
   "ligne_fin": 90,
   "rang": 4,
   "section": "Règles non négociables",
   "titre": "Typage strict",
   "us": []
  },
  {
   "adr": [],
   "amendements": [],
   "corps": "`DomainError` / `ApplicationError` / `InfrastructureError` /\n   `ApiError`. Le mapping HTTP se fait **uniquement à la frontière API**, réponse\n   `{ code, message, details? }`. Aucun message interne ne fuit vers le client (log serveur).",
   "fichier": "CLAUDE.md",
   "identifiant": "erreurs-typees-par-couche",
   "ligne": 91,
   "ligne_fin": 93,
   "rang": 5,
   "section": "Règles non négociables",
   "titre": "Erreurs typées par couche",
   "us": []
  },
  {
   "adr": [],
   "amendements": [],
   "corps": "DTO Pydantic **distincts** des entités domaine/ORM (jamais d'exposition\n   directe). REST versionné `/api/v1/…`. Les `Depends` restent cantonnés à la couche API.",
   "fichier": "CLAUDE.md",
   "identifiant": "frontiere-api",
   "ligne": 94,
   "ligne_fin": 95,
   "rang": 6,
   "section": "Règles non négociables",
   "titre": "Frontière API",
   "us": []
  },
  {
   "adr": [],
   "amendements": [],
   "corps": "WAL ; écritures **via la file consommée par le writer unique** ;\n   lectures synchrones hors boucle événementielle ; transactions **courtes**, pas de logique métier\n   longue dans une transaction ouverte. Pas d'aiosqlite. Migrations Alembic.",
   "fichier": "CLAUDE.md",
   "identifiant": "sqlite-single-writer",
   "ligne": 96,
   "ligne_fin": 98,
   "rang": 7,
   "section": "Règles non négociables",
   "titre": "SQLite single-writer",
   "us": []
  },
  {
   "adr": [],
   "amendements": [],
   "corps": "Câblage à la main dans `bootstrap/` / `main.py`, sans DI magique.\n   Tout nouveau branchement y est reflété.",
   "fichier": "CLAUDE.md",
   "identifiant": "composition-root-explicite",
   "ligne": 99,
   "ligne_fin": 100,
   "rang": 8,
   "section": "Règles non négociables",
   "titre": "Composition root explicite",
   "us": []
  },
  {
   "adr": [
    "0014"
   ],
   "amendements": [
    {
     "adr": [
      "0014"
     ],
     "date": "2026-07-15",
     "motif": "Cas réel, tranché le 15/07/2026 en E02US002 : stories/ disait « pas supprimable sans avertissement », docs/fonctionnel/ « refus définitif ». Arbitrage : le refus définitif — stories/ a été aligné, le code livré ne changeait pas. Cf. ADR-0014, qui a aussi corrigé deux CA faux d'E02US002 au passage.",
     "nature": "cas réel",
     "origine": "incise",
     "reference": "",
     "us": [
      "E02US002"
     ]
    }
   ],
   "corps": "Unitaires en priorité sur le domaine (couverture élevée), intégration sur les adapters\n   et endpoints, déterministes (pas d'horloge ni d'aléa non maîtrisé). **L'oracle 120** (rejeu du\n   tournoi de `Tableaux.xlsx`) doit rester vert.\n   **Le test dérive du CA, jamais du code déjà écrit.** Ce qui empêche un test de consacrer un bug,\n   ce n'est pas l'identité de son auteur — le même agent implémente et teste — c'est la **source**\n   dont il dérive. Un test rédigé après coup en lisant l'implémentation ne fait que décrire\n   l'implémentation : si le CA a été mal compris, le test entérine le malentendu, et un relecteur\n   à qui l'on donnerait le même code en déduirait la même intention. D'où :\n   - **Domaine & service** (là où vit la règle métier) : tests écrits **depuis le CA**\n     (`stories/Exx-*.md`, puce « **CA** », complétée des « Notes ») **avant** d'implémenter.\n     [`docs/fonctionnel/`](docs/fonctionnel/) n'est **pas** une source de CA : c'est un **produit**\n     de l'US (scénario de recette rédigé pour un non-technicien, décrivant l'UI livrée). Il n'existe\n     pas encore quand le test s'écrit ; s'en servir comme oracle serait le piège de cette règle même,\n     un cran plus haut — dériver le test d'un artefact produit par l'implémentation. Il documente les\n     US **déjà livrées** et sert de référence de comportement existant (utile en non-régression).\n   - **API, repository, câblage** : tests après l'implémentation — il n'y a pas d'oracle en jeu.\n   - **Non-régression** : l'oracle *est* le comportement actuel ; l'implémenteur est le meilleur\n     auteur, il connaît les coutures. Aucune indépendance à aller chercher.\n   - **Ne pas réussir à écrire le test depuis le CA est le signal que le CA est ambigu** — pas une\n     invitation à deviner. C'est un arbitrage : questionner l'utilisateur **avant** d'implémenter\n     (cf. § Workflow). Le flou se voit en rédigeant le test, pas à mi-parcours du code.\n   - **Un arbitrage tranché en cours d'US est reversé dans `stories/`** (puce « CA » ou « Notes »)\n     **dans le même commit** — pas seulement dans `docs/fonctionnel/`. Sans quoi le CA reste\n     **périmé** et l'US suivante en dérive ses tests : le garde-fou ci-dessus ne se déclenchera pas,\n     puisqu'un CA périmé n'est pas *ambigu* — il s'écrit sans effort, et il est faux. Une divergence\n     `stories/` ↔ `docs/fonctionnel/` est un **défaut à remonter**, jamais à arbitrer seul.\n     *(Cas réel, tranché le 15/07/2026 en E02US002 : `stories/` disait « pas supprimable **sans\n     avertissement** », `docs/fonctionnel/` « refus **définitif** ». Arbitrage : le refus définitif\n     — `stories/` a été aligné, le code livré ne changeait pas. Cf. [ADR-0014](docs/adr/0014-club-inconnu-plutot-que-club-sentinelle.md),\n     qui a aussi corrigé deux CA faux d'E02US002 au passage.)*",
   "fichier": "CLAUDE.md",
   "identifiant": "tests",
   "ligne": 101,
   "ligne_fin": 130,
   "rang": 9,
   "section": "Règles non négociables",
   "titre": "Tests",
   "us": [
    "E02US002"
   ]
  },
  {
   "adr": [],
   "amendements": [],
   "corps": "État serveur via React Query, état UI local via Zustand, organisation **par\n    features** (pas par type technique). Ergonomie tactile prioritaire sur l'écran de saisie +\n    indicateur de connexion visible.",
   "fichier": "CLAUDE.md",
   "identifiant": "front-react",
   "ligne": 131,
   "ligne_fin": 133,
   "rang": 10,
   "section": "Règles non négociables",
   "titre": "Front React",
   "us": []
  },
  {
   "adr": [],
   "amendements": [],
   "corps": "Parcimonie — pas de lib « plaisir » : stdlib ou quelques lignes maison\n    préférées ; en cas de doute, on n'ajoute pas. Toute lib ajoutée est, **dans le même commit**,\n    (a) déclarée au manifeste (`pyproject.toml` source de vérité **+** `requirements.txt` régénéré\n    par `pip freeze --exclude-editable`, **jamais** édité à la main ; ou `package.json` +\n    `package-lock.json`), (b) justifiée, (c) sûre (`pip-audit`/`npm audit` verts, licence\n    permissive), (d) documentée dans [`docs/dependances.md`](docs/dependances.md). Une dépendance\n    fantôme ou non documentée est bloquante.",
   "fichier": "CLAUDE.md",
   "identifiant": "dependances-externes",
   "ligne": 134,
   "ligne_fin": 140,
   "rang": 11,
   "section": "Règles non négociables",
   "titre": "Dépendances externes",
   "us": []
  },
  {
   "adr": [],
   "amendements": [],
   "corps": "L'infra reste simple : mono-club, local. La rigueur va au\n    moteur métier, pas à l'outillage.",
   "fichier": "CLAUDE.md",
   "identifiant": "simplicite-assumee-hors-domaine",
   "ligne": 141,
   "ligne_fin": 142,
   "rang": 12,
   "section": "Règles non négociables",
   "titre": "Simplicité assumée hors domaine",
   "us": []
  },
  {
   "adr": [
    "0099"
   ],
   "amendements": [],
   "corps": "Un commentaire est le seul artefact\n    que **rien ne vérifie** — ni le compilateur, ni `mypy`, ni `eslint`, ni un test : une phrase\n    fausse y survit indéfiniment et se lit comme une preuve. Il ne survit donc que s'il satisfait\n    **au moins un** de ces trois tests ([ADR-0099](docs/adr/0099-le-code-porte-des-pointeurs-pas-le-raisonnement.md)) :\n    **(a) contrainte non déductible** du fichier (une valeur qui dérive d'un autre fichier, un\n    invariant tenu ailleurs) ; **(b) avertissement** — une modification d'apparence innocente\n    casserait quelque chose que le code ne peut pas dire seul ; **(c) renvoi** d'**une ligne** vers\n    l'ADR, la story ou l'entrée de dette qui porte le raisonnement.\n    Sortent : historique de revue (c'est `git`), citations de CA (c'est [`stories/`](stories/)),\n    justification d'existence (c'est [`docs/dette.md`](docs/dette.md)), raisonnement long (c'est\n    l'ADR), paraphrase du code (c'est un échec de nommage).\n    ⚠️ **On ne coupe que ce qui existe ailleurs** — sinon on **déplace d'abord**. Le risque est\n    asymétrique : un commentaire de trop coûte une lecture, un savoir perdu coûte une US.\n    ⚠️ La maxime « un code commenté se lit mal » vaut pour le *quoi* et le *comment*, **pas pour le\n    pourquoi** : aucun nommage ne dit qu'une constante dérive d'une règle CSS d'une autre feature.\n    Le corps de commit, lui, reste long — il est immuable, donc il ne diverge pas.\n    **Trois contraintes de forme, qui priment sur le jugement** (ADR-0099, amendé le 27/08/2026 —\n    la version « trois tests » seule n'avait retiré que **0,3 %** du volume en trois vagues) :\n    **(i) huit lignes au plus par bloc.** Au-delà, ce n'est plus un avertissement mais un\n    raisonnement : il part en ADR et le code garde un renvoi. Seule règle de commentaire du projet\n    qui soit **mesurable**, donc la seule qui ne dérivera pas — et **la seule mécanisée** : elle\n    est vérifiée des deux côtés, par `backend/tests/test_commentaires_bornes.py` et\n    `frontend/src/commentaires.test.ts`, l'un et l'autre **sans tolérance** depuis E00US027.\n    ⚠️ **Périmètre exact**, parce qu'une porte qui se croit plus large qu'elle n'est éteint la\n    vigilance : côté backend, **tout le code de production `.py`** (les cinq couches, `atlas/`,\n    `release/`, les points d'entrée) ; côté front, tout `frontend/src` en `.ts` / `.tsx` / `.css`,\n    **tests compris**. Restent dehors `backend/tests/`, `migrations/`, `kervignarc.spec` et\n    `frontend/eslint.config.js` — écart tracé, chiffré et justifié en `DETTE-088`.\n    **(ii) aucune docstring tautologique** — si elle ne dit rien de plus que la signature, elle\n    disparaît (`par_club(club_id) -> list[Archer]` n'a pas besoin de « renvoie les archers du club »).\n    **(iii) un seul avertissement par bloc** — **indicateur de revue, non mécanisé**, et la nuance\n    compte : trois ⚠️ empilés signalent un module qui fait trop de choses ou un raisonnement à\n    sortir, mais la contrainte (i) **pousse en sens inverse** (fusionner pour tenir en huit lignes\n    empile les ⚠️). E00US027 s'est livrée en violant (iii) 153 fois : une règle démentie par son\n    propre commit d'introduction ne se tient plus jamais. On la relève donc à la lecture, on ne la\n    compte pas.",
   "fichier": "CLAUDE.md",
   "identifiant": "commentaires-pointeurs",
   "ligne": 143,
   "ligne_fin": 179,
   "rang": 13,
   "section": "Règles non négociables",
   "titre": "Le code porte des pointeurs, pas le raisonnement",
   "us": [
    "E00US027"
   ]
  },
  {
   "adr": [],
   "amendements": [],
   "corps": "**La forme reconnue est le jeton\n`DETTE-nnn` où qu'il soit dans le commentaire**, pas seulement en tête de ligne : le geste de\nrésorption est un `grep DETTE-nnn`, et exiger `# ` en tête ferait rater les sites où le marqueur\nvit à l'intérieur d'une phrase *(précisé en revue d'E00US027 — les deux conventions coexistaient\nsans être dites, ce qui rendait le grep de résorption faux)*. Une US qui **aggrave** une dette déjà\nlistée élargit la ligne existante au lieu d'inventer un contournement local. Une dette silencieuse\nest remontée en **majeur** à la revue ; ce qui casse un cas utilisateur réel dès maintenant n'est pas\nde la dette mais un **bloquant** à corriger avant merge. Le registre n'est pas une liste de tâches :\nun bug corrigeable dans l'US se corrige dans l'US.",
   "fichier": "CLAUDE.md",
   "identifiant": "registre-de-dette",
   "ligne": 182,
   "ligne_fin": 193,
   "rang": 1,
   "section": "Dette",
   "titre": "Une dette assumée (technique ou de conception) s'inscrit au registre […]",
   "us": [
    "E00US027"
   ]
  },
  {
   "adr": [],
   "amendements": [],
   "corps": "« Dupliquer une 2ᵉ fois et attendre le 3ᵉ cas »\nest une réponse valide.",
   "fichier": "CLAUDE.md",
   "identifiant": "remede-structurel",
   "ligne": 194,
   "ligne_fin": 198,
   "rang": 2,
   "section": "Dette",
   "titre": "Un remède structurel (introduire un pattern) se propose sur preuve dans le code […]",
   "us": []
  },
  {
   "adr": [
    "0088"
   ],
   "amendements": [],
   "corps": "La localisation (« où est le service qui… », « quel\n  pattern suit l'existant ») part à l'agent [`localiser`](.claude/agents/localiser.md) : les fichiers\n  atterrissent dans *son* contexte, l'assistant ne reçoit que la conclusion. Un sous-agent qui\n  **localise** tourne sur un modèle moins cher ; un sous-agent qui **juge** — les relecteurs de\n  `/revue-us` — garde le modèle fort : c'est une barrière qualité, elle ne s'optimise pas. Ces\n  modèles sont **épinglés au frontmatter** des agents, jamais hérités de la session\n  ([ADR-0088](docs/adr/0088-les-sous-agents-du-depot-sont-versionnes-et-a-modele-epingle.md)) : sans\n  cela, un `/model sonnet` choisi pour une US mécanique dégradait sa propre revue en silence.",
   "fichier": "CLAUDE.md",
   "identifiant": "deleguer-la-lecture-garder-le-jugement",
   "ligne": 206,
   "ligne_fin": 213,
   "rang": 1,
   "section": "Économie de contexte",
   "titre": "Déléguer la lecture, garder le jugement",
   "us": []
  },
  {
   "adr": [],
   "amendements": [],
   "corps": "[`docs/dette.md`](docs/dette.md),\n  [`docs/referentiel-ffta.md`](docs/referentiel-ffta.md) et\n  [`docs/modele-de-donnees.md`](docs/modele-de-donnees.md) pèsent ~20 Ko chacun : `Grep`, ou `Read`\n  avec offset, sur la partie qui concerne l'US — pas le fichier entier. Le registre de dette se\n  consulte par sa **table** « Dette ouverte » (4 Ko) ; on ne déplie une section « Détail » (14 Ko à\n  elles toutes) que pour une dette réellement en jeu.",
   "fichier": "CLAUDE.md",
   "identifiant": "lire-les-gros-documents-par-la-section-utile",
   "ligne": 214,
   "ligne_fin": 219,
   "rang": 2,
   "section": "Économie de contexte",
   "titre": "Lire les gros documents par la section utile",
   "us": []
  },
  {
   "adr": [],
   "amendements": [],
   "corps": "Une décision qui ne vit que dans le contexte est perdue au premier\n  `/compact`. ADR, registre de dette, corps de commit, mémoire : c'est déjà la règle (§ Dette,\n  § Workflow) — c'en est aussi la raison économique. Le meilleur point de coupe est **« lance la\n  PR »** : le code est écrit, la trace d'exploration ne sert plus ; le signaler à l'utilisateur.",
   "fichier": "CLAUDE.md",
   "identifiant": "ecrire-avant-de-compacter",
   "ligne": 220,
   "ligne_fin": 223,
   "rang": 3,
   "section": "Économie de contexte",
   "titre": "Écrire avant de compacter",
   "us": []
  },
  {
   "adr": [],
   "amendements": [],
   "corps": "L'utilisateur développe sur\n  **plusieurs postes** et son point de suivi est **GitHub** : la mémoire locale de l'assistant\n  (`~/.claude/…`) est **par machine** et **ne voyage pas**. Donc toute règle, décision ou arbitrage\n  qui **cadre le projet** s'écrit dans un fichier **versionné** — `CLAUDE.md`, [`docs/adr/`](docs/adr/),\n  [`docs/dette.md`](docs/dette.md), [`stories/`](stories/), [`journal-d-avancement/`](journal-d-avancement/) —\n  pour **partir sur GitHub et se retrouver sur chaque poste**. La mémoire n'est qu'un **aide-mémoire\n  personnel du poste courant**, **jamais la source de vérité** d'une décision projet ; si un fait\n  mémorisé cadre le projet, son **exemplaire versionné dans le dépôt fait foi**. *(Cela **précise** le\n  point précédent : la mémoire reste un lieu d'écriture utile — elle **double** le dépôt pour ce poste\n  — mais pour ce qui cadre le projet, elle ne le **remplace** pas.)*",
   "fichier": "CLAUDE.md",
   "identifiant": "ce-qui-cadre-le-projet-va-dans-le-depot-pas-en-memoire-locale",
   "ligne": 224,
   "ligne_fin": 234,
   "rang": 4,
   "section": "Économie de contexte",
   "titre": "Ce qui cadre le projet va dans le dépôt, pas en mémoire locale",
   "us": []
  },
  {
   "adr": [],
   "amendements": [],
   "corps": "jamais de travail direct sur `main`. Nommage\n  `\u003ctype>/\u003cExxUSyyy>-\u003cslug-court>` en minuscules kebab-case (ex. `feat/e04us003-saisie-fleches`).\n  `\u003ctype>` ∈ `feat` | `fix` | `refactor` | `test` | `docs` | `chore`, cohérent branche ↔ commits ↔ US.",
   "fichier": "CLAUDE.md",
   "identifiant": "une-branche-par-us",
   "ligne": 237,
   "ligne_fin": 239,
   "rang": 1,
   "section": "Workflow",
   "titre": "Une branche par US",
   "us": []
  },
  {
   "adr": [],
   "amendements": [],
   "corps": "`\u003ctype>(\u003cscope>): \u003crésumé>` (impératif, ≤ ~72 car., `scope` = ID d'US\n  en minuscules) + corps expliquant le **quoi** et surtout le **pourquoi**, avec les références\n  (`US: ExxUSyyy`, `ADR-XXXX`). Commits atomiques.",
   "fichier": "CLAUDE.md",
   "identifiant": "commits-conventionnels",
   "ligne": 240,
   "ligne_fin": 242,
   "rang": 2,
   "section": "Workflow",
   "titre": "Commits conventionnels",
   "us": []
  },
  {
   "adr": [],
   "amendements": [],
   "corps": "branche, implémentation, message de\n  commit rédigé, `git commit`, `git push`. Il **ne rend pas la main** pour ces étapes. Restent hors\n  de cette autonomie : `git rebase` (réécrit l'historique — zone critique) et tout ajout de\n  dépendance (`pip install` / `npm install` — cf. règle 11, c'est un arbitrage, pas de la\n  plomberie). `git merge` n'est pas un point d'arbitrage mais l'**étape de l'utilisateur** : c'est\n  lui qui merge la PR (bullet suivante).",
   "fichier": "CLAUDE.md",
   "identifiant": "l-assistant-deroule-le-cycle-d-une-us-en-autonomie",
   "ligne": 243,
   "ligne_fin": 248,
   "rang": 3,
   "section": "Workflow",
   "titre": "L'assistant déroule le cycle d'une US en autonomie",
   "us": []
  },
  {
   "adr": [
    "0013"
   ],
   "amendements": [],
   "corps": "L'assistant rédige **titre et corps** de la\n  PR ; il l'**ouvre lui-même si l'outillage du poste le permet** (`gh` authentifié), sinon il livre\n  le lien `pull/new/\u003cbranche>` prêt à coller. Le résultat est le même des deux côtés : **c'est\n  l'utilisateur qui merge**, puis dit « c'est mergé ».\n  *(La disponibilité de `gh` est un **fait de poste** — l'utilisateur développe sur plusieurs\n  machines. Elle ne s'inscrit donc jamais ici : ce fichier voyage, le poste non.)*",
   "fichier": "CLAUDE.md",
   "identifiant": "lancer-la-pr",
   "ligne": 249,
   "ligne_fin": 258,
   "rang": 4,
   "section": "Workflow",
   "titre": "Quand l'utilisateur dit « lance la PR », exécuter /revue-us : revue du diff par […]",
   "us": []
  },
  {
   "adr": [],
   "amendements": [
    {
     "adr": [],
     "date": "2026-07-29",
     "motif": "Ajouté le 29/07/2026 : la règle antérieure ne parlait que d'« arbitrage », donc ne couvrait pas ce cas — il s'était présenté deux fois dans la même journée.",
     "nature": "ajout",
     "origine": "incise",
     "reference": "",
     "us": []
    }
   ],
   "corps": "L'assistant fait avancer le code de\n  bout en bout ; il ne **rend la main que** :\n  1. **Zone critique** — action difficilement réversible ou à fort impact : suppression de branches\n     ou de fichiers non fusionnés, réécriture d'historique, purge, migration destructrice,\n     manipulation du dépôt d'un autre agent, tout ce qui sort vers l'extérieur.\n  2. **Il faut trancher** — choix métier, CA ambigu ou insatisfaisable en l'état, périmètre d'US,\n     ajout de dépendance (règle 11).\n  3. **Divergence de conception** — décision structurante (candidate à un ADR) ou écart au\n     [`guide-architecture.md`](guide-architecture.md).\n\n  Hors de ces trois cas, tout se décide et s'exécute sans lui : un doute purement technique se\n  tranche, se documente (registre de dette, corps de commit, ADR si structurant) et se signale\n  **après coup** — il n'interrompt pas.\n\n  **Le cas 1 se juge sur le risque, pas sur la nature de la décision.** C'est ce qui le distingue\n  des deux autres : une purge de branches ne pose aucune question d'architecture ni de métier, elle\n  est simplement difficile à défaire. *(Ajouté le 29/07/2026 : la règle antérieure ne parlait que\n  d'« arbitrage », donc ne couvrait pas ce cas — il s'était présenté deux fois dans la même journée.)*",
   "fichier": "CLAUDE.md",
   "identifiant": "autonomie-par-defaut-main-rendue-sur-trois-cas-seulement",
   "ligne": 259,
   "ligne_fin": 276,
   "rang": 5,
   "section": "Workflow",
   "titre": "Autonomie par défaut, main rendue sur trois cas seulement",
   "us": []
  },
  {
   "adr": [
    "0086"
   ],
   "amendements": [],
   "corps": "**L'atlas se régénère APRÈS le commit, dans deux cas où le hook ne peut structurellement rien\n  voir** (`cd backend && python -m atlas`, un commit d'une ligne) :\n  - **un commit qui déplace des lignes de `CLAUDE.md`** — l'historique d'une règle vient d'un\n    `git log -L \u003cbornes>`, et ces bornes sont résolues contre `HEAD`, donc contre le fichier\n    **d'avant** le commit. Le hook valide parce qu'il compare du périmé à du périmé : il est\n    auto-cohérent. Le fichier devient faux à l'instant du commit, et seule la CI le voit ;\n  - **deux PR en vol** : celle qui fusionne en **second** régénère avant son merge. Deux branches\n    peuvent n'avoir **aucun conflit git** — fichiers distincts, régions disjointes — et se périmer\n    mutuellement, il suffit que l'une ajoute un ADR et que l'autre ait généré ses cartes avant.\n\n  Sans ce geste, `main` part rouge. *(Les deux cas ont été constatés à la livraison même de\n  l'atlas, le second en revue — [ADR-0086](docs/adr/0086-un-atlas-genere-le-depot-cartographie-sans-dependance.md) § Conséquences.)*",
   "fichier": "CLAUDE.md",
   "identifiant": "cycle-de-branche",
   "ligne": 277,
   "ligne_fin": 289,
   "rang": 6,
   "section": "Workflow",
   "titre": "Cycle : branche depuis main à jour → PR → revue + CI verte → merge → […]",
   "us": []
  },
  {
   "adr": [],
   "amendements": [],
   "corps": "c'est le **point de reprise** de « reprend les US » (état de chaque US,\n  prochaine à prendre). Une US passe à ✅ **dans son propre dernier commit, une fois la revue\n  (`/revue-us`) faite et poussée** — l'assistant n'attend pas la confirmation « c'est mergé ». Le\n  procédé reste sûr parce que la mise à jour **voyage avec le diff de l'US** : elle n'atteint `main`\n  qu'**au merge de la PR**, donc `main` affiche le ✅ exactement quand l'US y arrive — jamais avant.\n  Sur la branche, le tracker est optimiste d'un cran (c'est le livrable) ; sur `main`, il reste\n  toujours vrai. Le même commit **pointe la 🎯 suivante** et ajuste les compteurs, de sorte qu'après un\n  `/clear` + « lance l'US suivante », l'assistant lise directement l'état sur `main` — recoupé au\n  besoin par `git log main --first-parent` / `git branch -r` (une US peut avoir été livrée par une\n  session parallèle). Un tracker périmé fait repartir « reprend les US » sur une base fausse : sa mise\n  à jour n'est pas cosmétique, elle conditionne la reprise.",
   "fichier": "CLAUDE.md",
   "identifiant": "suivi-des-us",
   "ligne": 290,
   "ligne_fin": 301,
   "rang": 7,
   "section": "Workflow",
   "titre": "Le suivi des US (journal-d-avancement/SUIVI-US.md) est tenu à jour dès que […]",
   "us": []
  },
  {
   "adr": [],
   "amendements": [
    {
     "adr": [],
     "date": "2026-07-21",
     "motif": "Manqué sur E12US007 le 21/07/2026 : le résumé n'a pas été mis à jour dans le commit de l'US — d'où cette porte explicite.",
     "nature": "manquement",
     "origine": "incise",
     "reference": "",
     "us": [
      "E12US007"
     ]
    },
    {
     "adr": [],
     "date": "2026-07-21",
     "motif": "Règle resserrée le 21/07/2026 à la demande du commanditaire : passage d'un fichier daté réservé aux jalons à un par US visible — le suivi gagne un récit par US, au prix d'un fichier de plus à maintenir. Pas de rattrapage rétroactif : appliquée aux US suivantes.",
     "nature": "resserrement",
     "origine": "incise",
     "reference": "",
     "us": []
    }
   ],
   "corps": "— c'est la photo d'ensemble rendue au commanditaire (« qu'est-ce qui marche\n  aujourd'hui »), en français non technique. Il se tient à jour **au même titre et par le même\n  mécanisme que `SUIVI-US.md`** : la mise à jour **voyage avec le diff de l'US**, dans son dernier\n  commit, donc sur `main` le journal reste **toujours vrai**. Concrètement, une US qui livre une\n  **fonctionnalité visible** met à jour, dans son propre commit :\n  - [`00-resume-projet.md`](journal-d-avancement/00-resume-projet.md) — le résumé « où on en est » :\n    la ou les fonctionnalités livrées, l'« état en une phrase », et les **chiffres repères**. Un résumé\n    qui liste moins de fonctionnalités que le tracker n'affiche de ✅ est **périmé** — défaut à\n    corriger, pas cosmétique. **`SUIVI-US.md` fait autorité sur le compte exact** (nombre d'US livrées,\n    dernière, prochaine) ; le résumé le **reflète** sans le contredire. Ne pas maintenir deux comptes\n    divergents — le doublon est lui-même une source de dérive : les deux fichiers se réconcilient\n    **dans le même commit**.\n  - un fichier daté `AAAA-MM-JJ-HHhMM-\u003cslug>.md` décrivant **ce que cette US livre**, en français non\n    technique — **un par US à surface visible**. Les US purement mécaniques **sans surface utilisateur**\n    (API, repository, câblage, refactor à rendu inchangé) **n'en produisent pas** : elles ne touchent que\n    les chiffres repères du résumé. Le fichier daté **raconte l'US** (ce qui est nouveau, pour qui, ce\n    que ça change pour l'organisateur ou le public) ; le résumé garde la **photo d'ensemble**. Le garder\n    **court** (quelques lignes) : c'est un récit d'US, pas un rapport — la concision remplace l'ancien\n    filtre « épisodique » pour éviter le fouillis. L'horodatage `HHhMM` se lit sur l'horloge système\n    (`date`), jamais inventé. *(Règle resserrée le 21/07/2026 à la demande du commanditaire : passage\n    d'un fichier daté réservé aux jalons à **un par US visible** — le suivi gagne un récit par US, au\n    prix d'un fichier de plus à maintenir. Pas de rattrapage rétroactif : appliquée aux US suivantes.)*\n\n  **Porte de revue (bloquant).** La mise à jour du journal d'un US à surface visible est **vérifiée à\n  `/revue-us`** au même titre que `SUIVI-US.md` : une US visible dont le diff **ne touche pas**\n  `00-resume-projet.md` **ou n'ajoute pas son fichier daté** est un **manquement à corriger avant la\n  PR**, pas un oubli tolérable — le livrable de suivi n'est un livrable que s'il est **toujours** rendu.\n  Le réflexe : avant de lancer la revue, se demander « ai-je mis à jour le résumé, ajouté le fichier\n  daté de l'US ET pointé le tracker ? » — les trois voyagent avec le diff,\n  jamais dans un commit séparé « docs » d'après-coup. *(Manqué sur E12US007 le 21/07/2026 : le résumé\n  n'a pas été mis à jour dans le commit de l'US — d'où cette porte explicite.)*",
   "fichier": "CLAUDE.md",
   "identifiant": "journal-d-avancement",
   "ligne": 302,
   "ligne_fin": 333,
   "rang": 8,
   "section": "Workflow",
   "titre": "Le journal d'avancement (journal-d-avancement/) est un livrable, pas des notes […]",
   "us": [
    "E12US007"
   ]
  },
  {
   "adr": [],
   "amendements": [
    {
     "adr": [],
     "date": "2026-07-20",
     "motif": "Cas réel, E07US006 le 20/07/2026 : CA « c'est moi », un archer, front-only ; l'intention réelle était « suivre plusieurs archers avec le déroulé du tour en direct » — backend + ADR. Redécoupé en deux tranches ; le cadrage aurait évité de brancher et d'explorer la version étroite d'abord.",
     "nature": "cas réel",
     "origine": "incise",
     "reference": "",
     "us": [
      "E07US006"
     ]
    }
   ],
   "corps": "Avant de brancher / explorer / coder une US qui\n  **livre une capacité vue par l'utilisateur**, reformuler en une ou deux lignes ce qu'elle délivre et\n  **demander si c'est bien tout le périmètre voulu — ou s'il en existe une version plus riche** —\n  surtout si le CA est ancien, mince ou purement front. Le besoin **émerge par le dialogue** (esprit\n  agile) : ne pas exiger de l'utilisateur qu'il ait tout anticipé dans la fiche, ni implémenter le CA\n  au pied de la lettre s'il sous-représente l'intention. Ce contrôle **complète** le garde-fou « CA\n  ambigu » (règle 9), qui ne détecte que l'**ambiguïté** : un CA **clair mais trop étroit** s'écrit\n  sans effort et passe au travers — c'est précisément ce cas qui gaspille de l'implémentation. Le\n  cadrage est **rapide** (une question, pas une cérémonie) et ne s'applique pas aux petites US\n  mécaniques sans surface utilisateur. *(Cas réel, E07US006 le 20/07/2026 : CA « c'est moi », un\n  archer, front-only ; l'intention réelle était « suivre plusieurs archers avec le déroulé du tour en\n  direct » — backend + ADR. Redécoupé en deux tranches ; le cadrage aurait évité de brancher et\n  d'explorer la version étroite d'abord.)*",
   "fichier": "CLAUDE.md",
   "identifiant": "cadrage-d-intention-en-tete-d-une-us-visible",
   "ligne": 334,
   "ligne_fin": 346,
   "rang": 9,
   "section": "Workflow",
   "titre": "Cadrage d'intention en tête d'une US visible",
   "us": [
    "E07US006"
   ]
  },
  {
   "adr": [
    "0017",
    "0075",
    "0028",
    "0049"
   ],
   "amendements": [
    {
     "adr": [
      "0017",
      "0075"
     ],
     "date": "2026-08-06",
     "motif": "Cas réel, 06/08/2026 : ADR-0017 décidait qu'« un départ rejoue le tournoi » ; seule la logistique l'a porté, le moteur a gardé la portée tournoi treize mois — un classement de 400 au lieu de quatre de 100. Cf. ADR-0075.",
     "nature": "cas réel",
     "origine": "incise",
     "reference": "",
     "us": []
    }
   ],
   "corps": "dans `docs/adr/` (contexte / décision / conséquences), **plus une\n  section « Porté dans le code par »** qui nomme les modules chargés de l'appliquer. Un ADR sans\n  cette section est une **intention**, pas une décision : rien ne permet de vérifier qu'il est tenu.\n  *(Cas réel, 06/08/2026 : [ADR-0017](docs/adr/0017-le-depart-est-un-creneau-du-tournoi.md) décidait\n  qu'« un départ rejoue le tournoi » ; seule la logistique l'a porté, le moteur a gardé la portée\n  tournoi **treize mois** — un classement de 400 au lieu de quatre de 100. Cf.\n  [ADR-0075](docs/adr/0075-le-depart-est-la-portee-sportive.md).)*\n\n  **Portée de la règle — le critère ici, l'énumération dans l'ADR.** La règle est née le 06/08/2026\n  et n'a **pas** été appliquée rétroactivement à tout le registre (8 ADR sur 81 la portaient). Elle\n  vaut pour **tout ADR neuf**, pour **tout ADR rouvert** (un diff qui touche sa section *Décision*\n  ou *Conséquences*), et pour les **ADR structurants encore actifs** — statut *Accepté* non\n  remplacé, **et** décision appliquée par le moteur sportif, la portée, ou une politique injectable\n  au sens de la règle 2. Les ADR d'outillage, d'UI, de procédure ou de convention documentaire\n  n'entrent pas dans le critère : **leur absence de section n'est pas un défaut à relever en\n  revue.**\n\n  **La liste nominative des ADR retenus vit dans\n  [ADR-0075 § « Portée de la règle »](docs/adr/0075-le-depart-est-la-portee-sportive.md)**, pas ici\n  — elle dérive à chaque US qui rouvre un ADR, et ce fichier n'est pas le bon endroit pour une liste\n  mouvante. Cet ADR porte aussi la **contrepartie** : la grille de `/revue-us` (axe C2, `12-ADR`)\n  exige la section sur tout ADR créé ou rouvert. Une règle qui borne ce qu'une revue peut relever\n  sans dire qui la vérifie ne fait que retirer de la détection.\n\n  ⚠️ **Écrire la section, c'est vérifier dans le code du jour, pas déduire de l'ADR.** Le\n  rétro-équipement l'a prouvé deux fois : `ADR-0028` (équipes) n'est porté **qu'au quart** — la\n  classe `Equipe` n'existe pas — et `ADR-0049` promet un barème résolu par « (phase, arme) » que le\n  code résout par l'**arme seule**. Nommer un module vide reproduit exactement le défaut\n  d'ADR-0017.",
   "fichier": "CLAUDE.md",
   "identifiant": "decision-structurante-adr",
   "ligne": 347,
   "ligne_fin": 375,
   "rang": 10,
   "section": "Workflow",
   "titre": "Décision structurante ⇒ ADR",
   "us": []
  },
  {
   "adr": [],
   "amendements": [],
   "corps": "",
   "fichier": "CLAUDE.md",
   "identifiant": "redecouper-une-us-trop-grosse",
   "ligne": 376,
   "ligne_fin": 377,
   "rang": 11,
   "section": "Workflow",
   "titre": "Une US trop grosse pour une branche doit être redécoupée (maille INVEST)",
   "us": []
  }
 ],
 "sections": [
  "Règles non négociables",
  "Dette",
  "Économie de contexte",
  "Workflow"
 ]
};
