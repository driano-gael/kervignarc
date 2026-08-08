# ADR-0054 — Exécution éphémère du moteur sur adapters in-memory des ports

- **Statut** : Accepté
- **Date** : 2026-07-28
- **Décideurs** : Organisateur / Architecte
- **Portée** : E15US002 (moteur de simulation éphémère + garde-fou de non-persistance)
- **Lie** : [ADR-0003](0003-architecture-hexagonale.md) (ports & adapters — c'est cette frontière
  qu'on rebranche), [ADR-0005](0005-async-et-sqlite.md) / règle 7 (single-writer — la
  contrainte que la simulation ne doit **pas** violer), [ADR-0026](0026-cycle-de-vie-du-tournoi-sept-statuts.md)
  (statuts — d'où le garde-fou), E15US001 (jeu d'essai — voisin : lui **persiste**, la simulation
  **non**)

## Contexte et problème

EPIC-15 veut **rejouer un tournoi entier** (qualification → duels → classement) pour la démo et la
QA, **sans jamais polluer les données réelles**. E15US002 en est le **cœur technique** : offrir un
substrat d'exécution du moteur qui écrit dans le vide, sur lequel E15US003 posera le bot pilote et le
cockpit.

Trois exigences se tendent :

1. **Ne rien persister** — aucune ligne SQLite, aucune diffusion temps réel du réel ne doit résulter
   d'une simulation.
2. **Rejouer le vrai moteur** — pas une ré-implémentation « pour la démo » qui divergerait du code de
   production ; c'est le même `ServiceClassement` / `ServicePlacementDuels` / `ServiceSaisieDuels`,
   les mêmes politiques (serpent / byes / élimination sèche), qui doivent tourner.
3. **Rester dans les règles** — en particulier la **règle 7** (single-writer) : l'option naïve
   « ouvrir une transaction, tout jouer, `ROLLBACK` » monopoliserait le writer unique pendant toute
   une simulation (transaction longue) et gèlerait le tournoi réel. Écartée d'emblée.

## Décision

**1. Rebrancher les mêmes services sur des adapters in-memory des ports (Option A).** Les services du
moteur ne dépendent que de **ports** (`domain/ports.py`) et de politiques **pures** — le spike l'a
confirmé : aucun ne touche SQLite ni la `write_queue`, seule la couche API soumet à la file. Il
suffit donc de les instancier sur un **jeu d'adapters in-memory** (magasins `dict`) au lieu des
adapters SQL. « Ne rien persister » devient une propriété **structurelle**, pas une discipline à
tenir : les écritures du moteur (poser un plan de duels, enregistrer un tir) atterrissent dans des
`dict` jetés à la fin — il n'existe aucun chemin de ces adapters vers la base.

**2. Les adapters in-memory sont du code de production, dans `infrastructure/memory/`.** Un adapter
est de l'infrastructure (règle 2) ; le domaine reste pur. Ils implémentent les **11 ports** du chemin
qualif → duels → classement : `Tournoi`, `Archer`, `Categorie`, `Blason`, `GabaritSalle`,
`Inscription`, `Phase`, `Serie`, `Forfait`, `Duel`, `PlacementTableau`.

*Pourquoi ne pas réutiliser les `Faux*Repository` des tests ?* Le CA le suggérait, mais le code de
production **ne peut pas importer `tests/`** (dépendance interdite). L'inverse — promouvoir les
doublures de test en adapters de production et faire importer les tests — dédupliquerait, mais au prix
d'un refactor transverse de nombreux modules de test (les doublures du moteur sont éparses, importées
d'un module à l'autre) : un **remède structurel** qui se traite en US dédiée sur preuve, pas en douce
dans celle-ci (règle 12, § Dette). On assume donc une **duplication** ciblée entre ces adapters et les
doublures de test, tenue honnête par les **tests de conformité de port** (cf. point 5).

**3. Hydratation par lecture, jamais par écriture.** `ServiceSimulation` reçoit les adapters **SQL
réels** en **lecture seule** ; il lit le tournoi choisi (archers, catégories, blasons, gabarit,
inscriptions, phases, séries, forfaits) et **recopie** dans les adapters in-memory, en **préservant
les identifiants** (l'intégrité référentielle — `archer.categorie_id`, etc. — en dépend). Les
lectures ne passent pas par la file (règle 7 : seules les écritures y transitent). Duels et plans de
duels ne sont **pas** hydratés : le garde-fou (point 4) garantit un tournoi **avant démarrage**, où
ils sont toujours vides.

**4. Garde-fou : simuler un tournoi *avant démarrage* seulement.** Lancer une simulation sur un
tournoi `en_cours`, `en_pause`, `terminé`, `archivé` ou `annulé` est **refusé**
(`SimulationTournoiDemarre`, 409) ; seuls `brouillon` et `prêt` sont simulables. Même borne, même
famille et même justification que `PeuplementTournoiDemarre` d'E15US001 : on ne mêle pas l'outil de
démo à une compétition vivante ou figée. L'arbitrage laissé ouvert par le CA (« terminé/archivé
simulable ? ») est **tranché : non** — cohérent avec l'invariant d'épic « ne pollue jamais le réel »
et avec le garde-fou du peuplement.

**5. Anti-dérive par tests de conformité de port partagés.** Le risque d'un jeu d'adapters parallèle,
c'est qu'il **diverge** de la sémantique SQL (un `par_tournoi` qui ne filtre pas, un `par_id`
introuvable qui ne renvoie pas `None`). Un **contrat de test paramétré** vérifie donc les mêmes
propriétés sur l'adapter SQL **et** l'adapter in-memory. On l'établit sur un sous-ensemble
représentatif (filtrage `par_tournoi`, `par_id` absent, ordre) ; il est **extensible** port par port.

**6. Diffusion isolée : rien à faire ici.** La diffusion temps réel est **exclusivement** couplée au
listener post-commit de la `write_queue` réelle. Une simulation ne soumet jamais à la file : **aucun**
`LiveEvent` réel n'est émis, sans code dédié. Le **canal séparé** pour pousser l'état *simulé* au
front relève d'E15US003 (cockpit) ; cet ADR se contente de garantir la **non-émission** côté réel.

## Conséquences

**Positives.**

- Non-persistance et non-diffusion **par construction** — pas une invariant à surveiller.
- Le moteur simulé **est** le moteur de production : pas de second moteur à maintenir, l'oracle 120
  reste l'oracle.
- Règle 7 respectée : aucune transaction longue, la simulation vit **hors** de la file.
- Substrat réutilisable : E15US003 écrit ses scores de bot dans les mêmes adapters in-memory.

**Négatives / limites.**

- **Duplication délibérée, pas dette tracée.** Les adapters in-memory et les doublures `Faux*` des
  tests forment deux jeux de magasins `dict` conformes aux mêmes ports. C'est la **2ᵉ occurrence** du
  motif « double de port en mémoire » : la **règle 16** du projet tranche ce cas (« dupliquer une 2ᵉ
  fois et attendre le 3ᵉ cas est une réponse valide »), donc **aucune dette n'est inscrite** au
  registre et **aucun pattern n'est introduit** ici. La cohérence est tenue par mypy (conformité de
  type aux ports) et par les tests de conformité de port (conformité de comportement). Un remède
  structurel (fusionner les deux jeux) ne se traitera qu'en **US dédiée sur 3ᵉ preuve** — pas avant.
- L'**hydratation** est un chemin de lecture **nouveau** (SQL → in-memory) : tout port ajouté au
  chemin du moteur devra y être recopié. Le garde-fou (avant démarrage) borne ce qu'il faut hydrater.

**Écartées.**

- **Transaction + `ROLLBACK`** : viole la règle 7 (transaction longue monopolisant le writer). Rejetée
  au niveau épic.
- **Base SQLite temporaire par simulation** : plus lourd (fichier, migrations, cycle de vie) qu'un jeu
  de `dict`, et rouvrirait la porte à une vraie persistance parasite ; l'in-memory est plus sûr et plus
  simple (règle 12).
