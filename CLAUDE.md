# Kervignarc — instructions pour l'assistant

Gestion de tournoi de tir à l'arc en salle (18 m) : outil interne mono-club, déployé le jour J sur
réseau local **sans internet**. Backend FastAPI (serveur autoritaire) + SPA React servie par lui,
temps réel par WebSocket, ~30 tablettes BYOD.

> **Le [`guide-architecture.md`](guide-architecture.md) fait autorité** sur la structure et le style.
> Ce fichier n'est qu'un rappel opérationnel : en cas de divergence, le guide gagne, et toute
> exception à une règle passe par un ADR (`docs/adr/`).

## Communication avec l'utilisateur

Le projet est **en français** : code métier, documentation, commits, PR, et les échanges.

Ce projet est aussi un **apprentissage du développement assisté par IA** : la façon dont le travail
est expliqué compte autant que le code produit. En conséquence :

- **Sois explicatif.** Ne te contente pas de livrer le diff : dis ce que tu as fait, **pourquoi** tu
  l'as fait ainsi, et quelles alternatives tu as écartées. Une réponse qui laisse l'utilisateur
  incapable de refaire le raisonnement seul a raté sa cible.
- **Langage technique, niveau développeur junior.** Emploie les vrais termes (port, adapter,
  invariant, agrégat, injection de politique, migration) — ne les édulcore pas — mais **explique-les
  au passage** la première fois qu'ils apparaissent dans un contexte donné. Le but est que le
  vocabulaire soit acquis, pas contourné.
- **Rattache les décisions aux règles.** Quand un choix découle d'une règle du projet ou d'un ADR,
  nomme-la explicitement (« le domaine ne peut pas importer SQLAlchemy — règle 1, d'où le port ») :
  c'est ce lien qui fait comprendre l'architecture plutôt que de la subir.
- **Signale les pièges et les raisons de se méfier.** Cas limites, effets de bord, ce qui cassera
  plus tard — y compris quand l'utilisateur ne l'a pas demandé.
- **Reste honnête sur l'incertitude.** Si une approche est un pari ou si tu n'as pas vérifié quelque
  chose, dis-le franchement plutôt que d'affirmer. Un doute exprimé s'apprend ; une erreur assurée
  s'imite.
- **Ne cède pas sur le fond pour être pédagogique** : explication ≠ approximation, et détail ≠
  délayage. On explique le raisonnement, pas la syntaxe Python.

### Apprendre à piloter l'assistant

L'utilisateur veut aussi **apprendre à mieux se servir de l'assistant**. L'outil fait donc partie du
sujet, pas seulement le code :

- **Rends ton propre fonctionnement visible.** Quand une demande te fait choisir une stratégie
  (déléguer à un sous-agent, lancer `/revue-us`, explorer avant d'éditer, passer par un plan), dis
  **pourquoi** ce chemin plutôt qu'un autre. C'est ce qui rend le pilotage reproductible.
- **Signale ce qui aurait mieux marché.** Si une demande était ambiguë, sous-spécifiée, ou t'a fait
  partir sur une fausse piste, dis-le **après coup**, avec la formulation qui t'aurait mis sur les
  rails du premier coup. Ne fais pas semblant que tout était clair.
- **Expose les leviers au moment utile** — commande, skill, mode plan, fichier de contexte, découpage
  de la demande. Au moment où ils servent, pas en catalogue théorique.
- **Dis ce que tu ne peux pas faire**, ou ce que tu fais mal : contexte que tu n'as pas, vérification
  que tu n'as pas pu mener, endroit où une relecture humaine reste indispensable. Connaître les
  limites de l'outil fait partie de savoir l'utiliser.
- **Corrige les usages contre-productifs.** Si une habitude de prompt dégrade le résultat (demande
  trop large, plusieurs sujets mêlés, contrainte implicite jamais énoncée), signale-le franchement au
  lieu de faire de ton mieux en silence.

## Commandes

```bash
# Backend (depuis backend/, venv activé)
pip install -e ".[dev]"
uvicorn main:app --reload     # http://127.0.0.1:8000  (santé : /health)
pytest
mypy --strict --config-file=pyproject.toml .
ruff check . && ruff format .

# Frontend (depuis frontend/)
npm run dev / build / lint / format / typecheck

# Application complète (proche production, port fixe)
cd backend && python run_dev.py        # --no-build réutilise frontend/dist/
```

`pre-commit` (racine) lance ruff, mypy strict, le garde-fou d'isolation du domaine, eslint et
prettier avant chaque commit. La CI GitHub Actions est **bloquante** sur PR et sur `main`.

## Règles non négociables

1. **Isolation du domaine.** <!--regle:isolation-du-domaine--> `backend/domain/` n'importe **aucun** framework (FastAPI, SQLAlchemy,
   Pydantic) ni aucune autre couche (`api/`, `application/`, `infrastructure/`, `bootstrap/`). Pur et
   synchrone. Vérifié par `backend/tests/test_domain_isolation.py` (AST) en pre-commit et en CI.
2. **Sens des dépendances.** <!--regle:sens-des-dependances--> Tout pointe vers le domaine. Les ports (interfaces) vivent dans le
   domaine, les adapters dans `infrastructure/`. Les politiques du moteur (`routing`, `scoring`,
   `seeding`, `byes`, `tiebreak`, `depth`) sont des stratégies injectables — un format de tournoi est
   de la **configuration**, pas du code.
3. **Vocabulaire.** <!--regle:vocabulaire--> Métier en **français FFTA** (`Archer`, `Cible`, `Blason`, `Volee`, `Fleche`,
   `Duel`, `Depart`, `Categorie`, `Phase`), technique en **anglais** (`Repository`, `Adapter`,
   `Service`, `Router`, `Store`). Cohérent entre code, API, UI et doc — voir
   [`docs/glossaire.md`](docs/glossaire.md).
4. **Typage strict.** <!--regle:typage-strict--> mypy strict côté Python (pas d'`Any` implicite), TS `strict` (pas d'`any` non
   justifié). Immutabilité privilégiée dans le domaine (dataclasses `frozen`).
5. **Erreurs typées par couche.** <!--regle:erreurs-typees-par-couche--> `DomainError` / `ApplicationError` / `InfrastructureError` /
   `ApiError`. Le mapping HTTP se fait **uniquement à la frontière API**, réponse
   `{ code, message, details? }`. Aucun message interne ne fuit vers le client (log serveur).
6. **Frontière API.** <!--regle:frontiere-api--> DTO Pydantic **distincts** des entités domaine/ORM (jamais d'exposition
   directe). REST versionné `/api/v1/…`. Les `Depends` restent cantonnés à la couche API.
7. **SQLite single-writer.** <!--regle:sqlite-single-writer--> WAL ; écritures **via la file consommée par le writer unique** ;
   lectures synchrones hors boucle événementielle ; transactions **courtes**, pas de logique métier
   longue dans une transaction ouverte. Pas d'aiosqlite. Migrations Alembic.
8. **Composition root explicite.** <!--regle:composition-root-explicite--> Câblage à la main dans `bootstrap/` / `main.py`, sans DI magique.
   Tout nouveau branchement y est reflété.
9. **Tests.** <!--regle:tests--> Unitaires en priorité sur le domaine (couverture élevée), intégration sur les adapters
   et endpoints, déterministes (pas d'horloge ni d'aléa non maîtrisé). **L'oracle 120** (rejeu du
   tournoi de `Tableaux.xlsx`) doit rester vert.
   **Le test dérive du CA, jamais du code déjà écrit.** Ce qui empêche un test de consacrer un bug,
   ce n'est pas l'identité de son auteur — le même agent implémente et teste — c'est la **source**
   dont il dérive. Un test rédigé après coup en lisant l'implémentation ne fait que décrire
   l'implémentation : si le CA a été mal compris, le test entérine le malentendu, et un relecteur
   à qui l'on donnerait le même code en déduirait la même intention. D'où :
   - **Domaine & service** (là où vit la règle métier) : tests écrits **depuis le CA**
     (`stories/Exx-*.md`, puce « **CA** », complétée des « Notes ») **avant** d'implémenter.
     [`docs/fonctionnel/`](docs/fonctionnel/) n'est **pas** une source de CA : c'est un **produit**
     de l'US (scénario de recette rédigé pour un non-technicien, décrivant l'UI livrée). Il n'existe
     pas encore quand le test s'écrit ; s'en servir comme oracle serait le piège de cette règle même,
     un cran plus haut — dériver le test d'un artefact produit par l'implémentation. Il documente les
     US **déjà livrées** et sert de référence de comportement existant (utile en non-régression).
   - **API, repository, câblage** : tests après l'implémentation — il n'y a pas d'oracle en jeu.
   - **Non-régression** : l'oracle *est* le comportement actuel ; l'implémenteur est le meilleur
     auteur, il connaît les coutures. Aucune indépendance à aller chercher.
   - **Ne pas réussir à écrire le test depuis le CA est le signal que le CA est ambigu** — pas une
     invitation à deviner. C'est un arbitrage : questionner l'utilisateur **avant** d'implémenter
     (cf. § Workflow). Le flou se voit en rédigeant le test, pas à mi-parcours du code.
   - **Un arbitrage tranché en cours d'US est reversé dans `stories/`** (puce « CA » ou « Notes »)
     **dans le même commit** — pas seulement dans `docs/fonctionnel/`. Sans quoi le CA reste
     **périmé** et l'US suivante en dérive ses tests : le garde-fou ci-dessus ne se déclenchera pas,
     puisqu'un CA périmé n'est pas *ambigu* — il s'écrit sans effort, et il est faux. Une divergence
     `stories/` ↔ `docs/fonctionnel/` est un **défaut à remonter**, jamais à arbitrer seul.
     *(Cas réel, tranché le 15/07/2026 en E02US002 : `stories/` disait « pas supprimable **sans
     avertissement** », `docs/fonctionnel/` « refus **définitif** ». Arbitrage : le refus définitif
     — `stories/` a été aligné, le code livré ne changeait pas. Cf. [ADR-0014](docs/adr/0014-club-inconnu-plutot-que-club-sentinelle.md),
     qui a aussi corrigé deux CA faux d'E02US002 au passage.)*
10. **Front React.** <!--regle:front-react--> État serveur via React Query, état UI local via Zustand, organisation **par
    features** (pas par type technique). Ergonomie tactile prioritaire sur l'écran de saisie +
    indicateur de connexion visible.
11. **Dépendances externes.** <!--regle:dependances-externes--> Parcimonie — pas de lib « plaisir » : stdlib ou quelques lignes maison
    préférées ; en cas de doute, on n'ajoute pas. Toute lib ajoutée est, **dans le même commit**,
    (a) déclarée au manifeste (`pyproject.toml` source de vérité **+** `requirements.txt` régénéré
    par `pip freeze --exclude-editable`, **jamais** édité à la main ; ou `package.json` +
    `package-lock.json`), (b) justifiée, (c) sûre (`pip-audit`/`npm audit` verts, licence
    permissive), (d) documentée dans [`docs/dependances.md`](docs/dependances.md). Une dépendance
    fantôme ou non documentée est bloquante.
12. **Simplicité assumée hors domaine.** <!--regle:simplicite-assumee-hors-domaine--> L'infra reste simple : mono-club, local. La rigueur va au
    moteur métier, pas à l'outillage.
13. **Le code porte des pointeurs, pas le raisonnement.** <!--regle:commentaires-pointeurs--> Un commentaire est le seul artefact
    que **rien ne vérifie** — ni le compilateur, ni `mypy`, ni `eslint`, ni un test : une phrase
    fausse y survit indéfiniment et se lit comme une preuve. Il ne survit donc que s'il satisfait
    **au moins un** de ces trois tests ([ADR-0099](docs/adr/0099-le-code-porte-des-pointeurs-pas-le-raisonnement.md)) :
    **(a) contrainte non déductible** du fichier (une valeur qui dérive d'un autre fichier, un
    invariant tenu ailleurs) ; **(b) avertissement** — une modification d'apparence innocente
    casserait quelque chose que le code ne peut pas dire seul ; **(c) renvoi** d'**une ligne** vers
    l'ADR, la story ou l'entrée de dette qui porte le raisonnement.
    Sortent : historique de revue (c'est `git`), citations de CA (c'est [`stories/`](stories/)),
    justification d'existence (c'est [`docs/dette.md`](docs/dette.md)), raisonnement long (c'est
    l'ADR), paraphrase du code (c'est un échec de nommage).
    ⚠️ **On ne coupe que ce qui existe ailleurs** — sinon on **déplace d'abord**. Le risque est
    asymétrique : un commentaire de trop coûte une lecture, un savoir perdu coûte une US.
    ⚠️ La maxime « un code commenté se lit mal » vaut pour le *quoi* et le *comment*, **pas pour le
    pourquoi** : aucun nommage ne dit qu'une constante dérive d'une règle CSS d'une autre feature.
    Le corps de commit, lui, reste long — il est immuable, donc il ne diverge pas.
    **Trois contraintes de forme, qui priment sur le jugement** (ADR-0099, amendé le 27/08/2026 —
    la version « trois tests » seule n'avait retiré que **0,3 %** du volume en trois vagues) :
    **(i) huit lignes au plus par bloc.** Au-delà, ce n'est plus un avertissement mais un
    raisonnement : il part en ADR et le code garde un renvoi. Seule règle de commentaire du projet
    qui soit **mesurable**, donc la seule qui ne dérivera pas — et **la seule mécanisée** : elle
    est vérifiée des deux côtés, par `backend/tests/test_commentaires_bornes.py` et
    `frontend/src/commentaires.test.ts`, l'un et l'autre **sans tolérance** depuis E00US027.
    ⚠️ **Périmètre exact**, parce qu'une porte qui se croit plus large qu'elle n'est éteint la
    vigilance : côté backend, **tout le code de production `.py`** (les cinq couches, `atlas/`,
    `release/`, les points d'entrée) ; côté front, tout `frontend/src` en `.ts` / `.tsx` / `.css`,
    **tests compris**. Restent dehors `backend/tests/`, `migrations/`, `kervignarc.spec` et
    `frontend/eslint.config.js` — écart tracé, chiffré et justifié en `DETTE-088`.
    **(ii) aucune docstring tautologique** — si elle ne dit rien de plus que la signature, elle
    disparaît (`par_club(club_id) -> list[Archer]` n'a pas besoin de « renvoie les archers du club »).
    **(iii) un seul avertissement par bloc** — **indicateur de revue, non mécanisé**, et la nuance
    compte : trois ⚠️ empilés signalent un module qui fait trop de choses ou un raisonnement à
    sortir, mais la contrainte (i) **pousse en sens inverse** (fusionner pour tenir en huit lignes
    empile les ⚠️). E00US027 s'est livrée en violant (iii) 153 fois : une règle démentie par son
    propre commit d'introduction ne se tient plus jamais. On la relève donc à la lecture, on ne la
    compte pas.

## Dette

<!--regle:registre-de-dette--> Une dette **assumée** (technique ou de conception) s'inscrit au registre
[`docs/dette.md`](docs/dette.md) **dans le commit qui l'introduit** : ligne au tableau + section de
détail + marqueur `DETTE-nnn` à l'endroit exact du raccourci. **La forme reconnue est le jeton
`DETTE-nnn` où qu'il soit dans le commentaire**, pas seulement en tête de ligne : le geste de
résorption est un `grep DETTE-nnn`, et exiger `# ` en tête ferait rater les sites où le marqueur
vit à l'intérieur d'une phrase *(précisé en revue d'E00US027 — les deux conventions coexistaient
sans être dites, ce qui rendait le grep de résorption faux)*. Une US qui **aggrave** une dette déjà
listée élargit la ligne existante au lieu d'inventer un contournement local. Une dette silencieuse
est remontée en **majeur** à la revue ; ce qui casse un cas utilisateur réel dès maintenant n'est pas
de la dette mais un **bloquant** à corriger avant merge. Le registre n'est pas une liste de tâches :
un bug corrigeable dans l'US se corrige dans l'US.

<!--regle:remede-structurel--> Un **remède structurel** (introduire un pattern) se propose sur **preuve dans le code d'aujourd'hui**
— 3ᵉ occurrence réelle, invariant déjà dupliqué — jamais sur une évolution supposée, et se traite en
ADR + US dédiée, jamais en douce dans l'US courante. « Dupliquer une 2ᵉ fois et attendre le 3ᵉ cas »
est une réponse valide.

## Économie de contexte

L'API est sans état : le contexte est **renvoyé en entier à chaque tour**. Une session à 150k tokens
paie ~15k tokens d'input à chaque échange — cache compris — avant d'avoir produit une ligne, et ce
qu'un outil y verse reste jusqu'à la fin. Ce ne sont pas ces docs qui le remplissent (~2 %), c'est la
**sortie des outils**. D'où :

- **Déléguer la lecture, garder le jugement.** <!--regle:deleguer-la-lecture-garder-le-jugement--> La localisation (« où est le service qui… », « quel
  pattern suit l'existant ») part à l'agent [`localiser`](.claude/agents/localiser.md) : les fichiers
  atterrissent dans *son* contexte, l'assistant ne reçoit que la conclusion. Un sous-agent qui
  **localise** tourne sur un modèle moins cher ; un sous-agent qui **juge** — les relecteurs de
  `/revue-us` — garde le modèle fort : c'est une barrière qualité, elle ne s'optimise pas. Ces
  modèles sont **épinglés au frontmatter** des agents, jamais hérités de la session
  ([ADR-0088](docs/adr/0088-les-sous-agents-du-depot-sont-versionnes-et-a-modele-epingle.md)) : sans
  cela, un `/model sonnet` choisi pour une US mécanique dégradait sa propre revue en silence.
- **Lire les gros documents par la section utile.** <!--regle:lire-les-gros-documents-par-la-section-utile--> [`docs/dette.md`](docs/dette.md),
  [`docs/referentiel-ffta.md`](docs/referentiel-ffta.md) et
  [`docs/modele-de-donnees.md`](docs/modele-de-donnees.md) pèsent ~20 Ko chacun : `Grep`, ou `Read`
  avec offset, sur la partie qui concerne l'US — pas le fichier entier. Le registre de dette se
  consulte par sa **table** « Dette ouverte » (4 Ko) ; on ne déplie une section « Détail » (14 Ko à
  elles toutes) que pour une dette réellement en jeu.
- **Écrire avant de compacter.** <!--regle:ecrire-avant-de-compacter--> Une décision qui ne vit que dans le contexte est perdue au premier
  `/compact`. ADR, registre de dette, corps de commit, mémoire : c'est déjà la règle (§ Dette,
  § Workflow) — c'en est aussi la raison économique. Le meilleur point de coupe est **« lance la
  PR »** : le code est écrit, la trace d'exploration ne sert plus ; le signaler à l'utilisateur.
- **Ce qui cadre le projet va dans le dépôt, pas en mémoire locale.** <!--regle:ce-qui-cadre-le-projet-va-dans-le-depot-pas-en-memoire-locale--> L'utilisateur développe sur
  **plusieurs postes** et son point de suivi est **GitHub** : la mémoire locale de l'assistant
  (`~/.claude/…`) est **par machine** et **ne voyage pas**. Donc toute règle, décision ou arbitrage
  qui **cadre le projet** s'écrit dans un fichier **versionné** — `CLAUDE.md`, [`docs/adr/`](docs/adr/),
  [`docs/dette.md`](docs/dette.md), [`stories/`](stories/), [`journal-d-avancement/`](journal-d-avancement/) —
  pour **partir sur GitHub et se retrouver sur chaque poste**. La mémoire n'est qu'un **aide-mémoire
  personnel du poste courant**, **jamais la source de vérité** d'une décision projet ; si un fait
  mémorisé cadre le projet, son **exemplaire versionné dans le dépôt fait foi**. *(Cela **précise** le
  point précédent : la mémoire reste un lieu d'écriture utile — elle **double** le dépôt pour ce poste
  — mais pour ce qui cadre le projet, elle ne le **remplace** pas.)*

## Workflow

- <!--regle:une-branche-par-us--> **Une branche par US**, jamais de travail direct sur `main`. Nommage
  `<type>/<ExxUSyyy>-<slug-court>` en minuscules kebab-case (ex. `feat/e04us003-saisie-fleches`).
  `<type>` ∈ `feat` | `fix` | `refactor` | `test` | `docs` | `chore`, cohérent branche ↔ commits ↔ US.
- **Commits conventionnels** <!--regle:commits-conventionnels--> : `<type>(<scope>): <résumé>` (impératif, ≤ ~72 car., `scope` = ID d'US
  en minuscules) + corps expliquant le **quoi** et surtout le **pourquoi**, avec les références
  (`US: ExxUSyyy`, `ADR-XXXX`). Commits atomiques.
- **L'assistant déroule le cycle d'une US en autonomie** <!--regle:l-assistant-deroule-le-cycle-d-une-us-en-autonomie--> : branche, implémentation, message de
  commit rédigé, `git commit`, `git push`. Il **ne rend pas la main** pour ces étapes. Restent hors
  de cette autonomie : `git rebase` (réécrit l'historique — zone critique) et tout ajout de
  dépendance (`pip install` / `npm install` — cf. règle 11, c'est un arbitrage, pas de la
  plomberie). `git merge` n'est pas un point d'arbitrage mais l'**étape de l'utilisateur** : c'est
  lui qui merge la PR (bullet suivante).
- <!--regle:lancer-la-pr--> Quand l'utilisateur dit **« lance la PR »**, exécuter [`/revue-us`](.claude/commands/revue-us.md) :
  revue du diff par des **agents dédiés en parallèle** (quatre axes + porte mécanique, plus un
  relecteur **adversarial** si le changement est structurel — [ADR-0013](docs/adr/0013-conduite-de-la-revue-d-us.md)),
  puis synthèse et correction par l'agent auteur,
  re-commit et push — sans repasser par l'utilisateur. L'assistant rédige **titre et corps** de la
  PR ; il l'**ouvre lui-même si l'outillage du poste le permet** (`gh` authentifié), sinon il livre
  le lien `pull/new/<branche>` prêt à coller. Le résultat est le même des deux côtés : **c'est
  l'utilisateur qui merge**, puis dit « c'est mergé ».
  *(La disponibilité de `gh` est un **fait de poste** — l'utilisateur développe sur plusieurs
  machines. Elle ne s'inscrit donc jamais ici : ce fichier voyage, le poste non.)*
- **Autonomie par défaut, main rendue sur trois cas seulement.** <!--regle:autonomie-par-defaut-main-rendue-sur-trois-cas-seulement--> L'assistant fait avancer le code de
  bout en bout ; il ne **rend la main que** :
  1. **Zone critique** — action difficilement réversible ou à fort impact : suppression de branches
     ou de fichiers non fusionnés, réécriture d'historique, purge, migration destructrice,
     manipulation du dépôt d'un autre agent, tout ce qui sort vers l'extérieur.
  2. **Il faut trancher** — choix métier, CA ambigu ou insatisfaisable en l'état, périmètre d'US,
     ajout de dépendance (règle 11).
  3. **Divergence de conception** — décision structurante (candidate à un ADR) ou écart au
     [`guide-architecture.md`](guide-architecture.md).

  Hors de ces trois cas, tout se décide et s'exécute sans lui : un doute purement technique se
  tranche, se documente (registre de dette, corps de commit, ADR si structurant) et se signale
  **après coup** — il n'interrompt pas.

  **Le cas 1 se juge sur le risque, pas sur la nature de la décision.** C'est ce qui le distingue
  des deux autres : une purge de branches ne pose aucune question d'architecture ni de métier, elle
  est simplement difficile à défaire. *(Ajouté le 29/07/2026 : la règle antérieure ne parlait que
  d'« arbitrage », donc ne couvrait pas ce cas — il s'était présenté deux fois dans la même journée.)*
- <!--regle:cycle-de-branche--> Cycle : branche depuis `main` à jour → PR → revue + CI verte → merge → suppression de la branche.
  **L'atlas se régénère APRÈS le commit, dans deux cas où le hook ne peut structurellement rien
  voir** (`cd backend && python -m atlas`, un commit d'une ligne) :
  - **un commit qui déplace des lignes de `CLAUDE.md`** — l'historique d'une règle vient d'un
    `git log -L <bornes>`, et ces bornes sont résolues contre `HEAD`, donc contre le fichier
    **d'avant** le commit. Le hook valide parce qu'il compare du périmé à du périmé : il est
    auto-cohérent. Le fichier devient faux à l'instant du commit, et seule la CI le voit ;
  - **deux PR en vol** : celle qui fusionne en **second** régénère avant son merge. Deux branches
    peuvent n'avoir **aucun conflit git** — fichiers distincts, régions disjointes — et se périmer
    mutuellement, il suffit que l'une ajoute un ADR et que l'autre ait généré ses cartes avant.

  Sans ce geste, `main` part rouge. *(Les deux cas ont été constatés à la livraison même de
  l'atlas, le second en revue — [ADR-0086](docs/adr/0086-un-atlas-genere-le-depot-cartographie-sans-dependance.md) § Conséquences.)*
- <!--regle:suivi-des-us--> **Le suivi des US ([`journal-d-avancement/SUIVI-US.md`](journal-d-avancement/SUIVI-US.md)) est tenu
  à jour dès que nécessaire** : c'est le **point de reprise** de « reprend les US » (état de chaque US,
  prochaine à prendre). Une US passe à ✅ **dans son propre dernier commit, une fois la revue
  (`/revue-us`) faite et poussée** — l'assistant n'attend pas la confirmation « c'est mergé ». Le
  procédé reste sûr parce que la mise à jour **voyage avec le diff de l'US** : elle n'atteint `main`
  qu'**au merge de la PR**, donc `main` affiche le ✅ exactement quand l'US y arrive — jamais avant.
  Sur la branche, le tracker est optimiste d'un cran (c'est le livrable) ; sur `main`, il reste
  toujours vrai. Le même commit **pointe la 🎯 suivante** et ajuste les compteurs, de sorte qu'après un
  `/clear` + « lance l'US suivante », l'assistant lise directement l'état sur `main` — recoupé au
  besoin par `git log main --first-parent` / `git branch -r` (une US peut avoir été livrée par une
  session parallèle). Un tracker périmé fait repartir « reprend les US » sur une base fausse : sa mise
  à jour n'est pas cosmétique, elle conditionne la reprise.
- <!--regle:journal-d-avancement--> **Le journal d'avancement ([`journal-d-avancement/`](journal-d-avancement/)) est un livrable, pas des
  notes internes** — c'est la photo d'ensemble rendue au commanditaire (« qu'est-ce qui marche
  aujourd'hui »), en français non technique. Il se tient à jour **au même titre et par le même
  mécanisme que `SUIVI-US.md`** : la mise à jour **voyage avec le diff de l'US**, dans son dernier
  commit, donc sur `main` le journal reste **toujours vrai**. Concrètement, une US qui livre une
  **fonctionnalité visible** met à jour, dans son propre commit :
  - [`00-resume-projet.md`](journal-d-avancement/00-resume-projet.md) — le résumé « où on en est » :
    la ou les fonctionnalités livrées, l'« état en une phrase », et les **chiffres repères**. Un résumé
    qui liste moins de fonctionnalités que le tracker n'affiche de ✅ est **périmé** — défaut à
    corriger, pas cosmétique. **`SUIVI-US.md` fait autorité sur le compte exact** (nombre d'US livrées,
    dernière, prochaine) ; le résumé le **reflète** sans le contredire. Ne pas maintenir deux comptes
    divergents — le doublon est lui-même une source de dérive : les deux fichiers se réconcilient
    **dans le même commit**.
  - un fichier daté `AAAA-MM-JJ-HHhMM-<slug>.md` décrivant **ce que cette US livre**, en français non
    technique — **un par US à surface visible**. Les US purement mécaniques **sans surface utilisateur**
    (API, repository, câblage, refactor à rendu inchangé) **n'en produisent pas** : elles ne touchent que
    les chiffres repères du résumé. Le fichier daté **raconte l'US** (ce qui est nouveau, pour qui, ce
    que ça change pour l'organisateur ou le public) ; le résumé garde la **photo d'ensemble**. Le garder
    **court** (quelques lignes) : c'est un récit d'US, pas un rapport — la concision remplace l'ancien
    filtre « épisodique » pour éviter le fouillis. L'horodatage `HHhMM` se lit sur l'horloge système
    (`date`), jamais inventé. *(Règle resserrée le 21/07/2026 à la demande du commanditaire : passage
    d'un fichier daté réservé aux jalons à **un par US visible** — le suivi gagne un récit par US, au
    prix d'un fichier de plus à maintenir. Pas de rattrapage rétroactif : appliquée aux US suivantes.)*

  **Porte de revue (bloquant).** La mise à jour du journal d'un US à surface visible est **vérifiée à
  `/revue-us`** au même titre que `SUIVI-US.md` : une US visible dont le diff **ne touche pas**
  `00-resume-projet.md` **ou n'ajoute pas son fichier daté** est un **manquement à corriger avant la
  PR**, pas un oubli tolérable — le livrable de suivi n'est un livrable que s'il est **toujours** rendu.
  Le réflexe : avant de lancer la revue, se demander « ai-je mis à jour le résumé, ajouté le fichier
  daté de l'US ET pointé le tracker ? » — les trois voyagent avec le diff,
  jamais dans un commit séparé « docs » d'après-coup. *(Manqué sur E12US007 le 21/07/2026 : le résumé
  n'a pas été mis à jour dans le commit de l'US — d'où cette porte explicite.)*
- **Cadrage d'intention en tête d'une US visible.** <!--regle:cadrage-d-intention-en-tete-d-une-us-visible--> Avant de brancher / explorer / coder une US qui
  **livre une capacité vue par l'utilisateur**, reformuler en une ou deux lignes ce qu'elle délivre et
  **demander si c'est bien tout le périmètre voulu — ou s'il en existe une version plus riche** —
  surtout si le CA est ancien, mince ou purement front. Le besoin **émerge par le dialogue** (esprit
  agile) : ne pas exiger de l'utilisateur qu'il ait tout anticipé dans la fiche, ni implémenter le CA
  au pied de la lettre s'il sous-représente l'intention. Ce contrôle **complète** le garde-fou « CA
  ambigu » (règle 9), qui ne détecte que l'**ambiguïté** : un CA **clair mais trop étroit** s'écrit
  sans effort et passe au travers — c'est précisément ce cas qui gaspille de l'implémentation. Le
  cadrage est **rapide** (une question, pas une cérémonie) et ne s'applique pas aux petites US
  mécaniques sans surface utilisateur. *(Cas réel, E07US006 le 20/07/2026 : CA « c'est moi », un
  archer, front-only ; l'intention réelle était « suivre plusieurs archers avec le déroulé du tour en
  direct » — backend + ADR. Redécoupé en deux tranches ; le cadrage aurait évité de brancher et
  d'explorer la version étroite d'abord.)*
- **Décision structurante ⇒ ADR** <!--regle:decision-structurante-adr--> dans `docs/adr/` (contexte / décision / conséquences), **plus une
  section « Porté dans le code par »** qui nomme les modules chargés de l'appliquer. Un ADR sans
  cette section est une **intention**, pas une décision : rien ne permet de vérifier qu'il est tenu.
  *(Cas réel, 06/08/2026 : [ADR-0017](docs/adr/0017-le-depart-est-un-creneau-du-tournoi.md) décidait
  qu'« un départ rejoue le tournoi » ; seule la logistique l'a porté, le moteur a gardé la portée
  tournoi **treize mois** — un classement de 400 au lieu de quatre de 100. Cf.
  [ADR-0075](docs/adr/0075-le-depart-est-la-portee-sportive.md).)*

  **Portée de la règle — le critère ici, l'énumération dans l'ADR.** La règle est née le 06/08/2026
  et n'a **pas** été appliquée rétroactivement à tout le registre (8 ADR sur 81 la portaient). Elle
  vaut pour **tout ADR neuf**, pour **tout ADR rouvert** (un diff qui touche sa section *Décision*
  ou *Conséquences*), et pour les **ADR structurants encore actifs** — statut *Accepté* non
  remplacé, **et** décision appliquée par le moteur sportif, la portée, ou une politique injectable
  au sens de la règle 2. Les ADR d'outillage, d'UI, de procédure ou de convention documentaire
  n'entrent pas dans le critère : **leur absence de section n'est pas un défaut à relever en
  revue.**

  **La liste nominative des ADR retenus vit dans
  [ADR-0075 § « Portée de la règle »](docs/adr/0075-le-depart-est-la-portee-sportive.md)**, pas ici
  — elle dérive à chaque US qui rouvre un ADR, et ce fichier n'est pas le bon endroit pour une liste
  mouvante. Cet ADR porte aussi la **contrepartie** : la grille de `/revue-us` (axe C2, `12-ADR`)
  exige la section sur tout ADR créé ou rouvert. Une règle qui borne ce qu'une revue peut relever
  sans dire qui la vérifie ne fait que retirer de la détection.

  ⚠️ **Écrire la section, c'est vérifier dans le code du jour, pas déduire de l'ADR.** Le
  rétro-équipement l'a prouvé deux fois : `ADR-0028` (équipes) n'est porté **qu'au quart** — la
  classe `Equipe` n'existe pas — et `ADR-0049` promet un barème résolu par « (phase, arme) » que le
  code résout par l'**arme seule**. Nommer un module vide reproduit exactement le défaut
  d'ADR-0017.
- <!--regle:redecouper-une-us-trop-grosse--> Une US trop grosse pour une branche doit être **redécoupée** (maille INVEST).

## Documents de référence

| Document | Contenu |
|---|---|
| [`guide-architecture.md`](guide-architecture.md) | **Conventions de code & workflow — fait autorité** |
| [`cahier-des-charges.md`](cahier-des-charges.md) | Besoin fonctionnel |
| [`cahier-des-charges-technique.md`](cahier-des-charges-technique.md) | Architecture technique |
| [`cahier-des-charges-ux.md`](cahier-des-charges-ux.md) · [`-design.md`](cahier-des-charges-design.md) | Parcours & registres `D-nn` / `DV-nn` |
| [`moteur-placement-lucky-loser.md`](moteur-placement-lucky-loser.md) | Formalisation du moteur de placement |
| [`docs/glossaire.md`](docs/glossaire.md) · [`docs/modele-de-donnees.md`](docs/modele-de-donnees.md) · [`docs/referentiel-ffta.md`](docs/referentiel-ffta.md) | Vocabulaire, modèle, règles FFTA |
| [`docs/dette.md`](docs/dette.md) · [`docs/dependances.md`](docs/dependances.md) · [`docs/adr/`](docs/adr/) | Registres et décisions |
| [`epics/`](epics/) · [`stories/`](stories/) | Backlog produit (jalons J0→J4) |
| [`journal-d-avancement/`](journal-d-avancement/) | **Livrable de suivi** : `SUIVI-US.md` (point de reprise) + `00-resume-projet.md` (photo d'ensemble) + faits marquants datés |

`prototype/` est un prototype Python de déc. 2024 : **référence de lecture uniquement**, non exécuté,
au vocabulaire hétérogène (`Player.lettre`, `idCible`) — ne pas s'en inspirer pour le nommage.
