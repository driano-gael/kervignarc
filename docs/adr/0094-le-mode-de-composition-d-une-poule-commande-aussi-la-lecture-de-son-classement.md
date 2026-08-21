# ADR-0094 — Le mode de composition d'une poule commande aussi la lecture de son classement

- **Statut** : Accepté
- **Date** : 2026-08-21
- **US** : E05US029
- **S'appuie sur** :
  [ADR-0083](0083-un-contrat-de-phase-decrit-ce-que-le-moteur-sait-faire.md) (§6, l'ordre « par rang
  de poule d'abord » — c'est très exactement la règle que cet ADR rend conditionnelle),
  [ADR-0080](0080-un-prelevement-lit-le-classement-de-sa-phase-source.md) (un prélèvement lit le
  classement de sa phase source : c'est ce qui rendait le format déjà composable en une étape par
  niveau),
  [ADR-0081](0081-une-phase-attend-que-sa-source-ait-departage-les-places-qu-elle-preleve.md) (la
  classe de défaut « bien formé, plausible, et faux », que le mauvais versant de ce mode produit),
  [ADR-0068](0068-le-moteur-consomme-les-prelevements-declares.md) (§5, `rang_premier` :
  l'espace de rangs est porté par la **phase**, et cet ADR explique pourquoi il n'a pas eu à
  descendre au groupe)
- **Voisin** : [ADR-0075](0075-le-depart-est-la-portee-sportive.md) — cet ADR est inscrit à sa liste
  nominative, au titre d'une décision appliquée par le moteur sportif

## Contexte

Le commanditaire a décrit, au cadrage d'`E05US026` du 15/08/2026, un format club en cascade :

> 36 archers. **Phase 1** : 6 poules de 6, disputant les rangs 1-36. **Phase 2** : 6 poules de 6,
> mais composées **par niveau** — les rangs 1-6, 7-12, 13-18, 19-24, 25-30, 31-36. Le classement de
> la phase 2 est alors le **classement final** du tournoi, exact de 1 à 36.

Ce format était **déjà composable** avant cette US, en écrivant une étape par niveau — six étapes,
chacune portant une poule et sa source (« les rangs 1 à 6 de la phase 1 »). Ce qui manquait n'était
donc pas une capacité mais un **confort de composition**. Deux obstacles s'opposaient à ce qu'une
seule étape se déplie en six groupes :

1. **Le serpent.** `composer_poules` répartissait en serpentin (1→A, 2→B, 3→C, 4→C, 5→B, 6→A) sans
   alternative. C'est un arbitrage explicite du 31/07/2026 : il **équilibre la force des groupes**,
   ce qui est juste en première phase — personne ne connaît encore les niveaux — et **faux** pour
   une phase de niveau, dont tout l'intérêt est que la poule A soit celle des meilleurs.
2. **L'espace de rangs.** `ResultatPhase.rang_premier` (ADR-0068 §5) vaut pour l'étape entière. Six
   poules de niveau dans une étape disputent six espaces de rangs distincts.

⚠️ **La fiche d'US énonçait le second obstacle d'une façon qui menait au mauvais remède** : elle
concluait qu'il fallait porter le décalage **au groupe**. La vérification dans le code a montré que
non — voir §2 — et cet ADR existe surtout pour consigner *pourquoi*, parce que le remède annoncé
aurait introduit une seconde vérité durable sur une notion (l'espace de rangs) dont ADR-0081 dit
qu'elle produit les défauts les plus coûteux du moteur.

## Décision

### §1 — Le mode de composition est un **réglage**, pas un type de phase

`ReglageDePoules` gagne `mode: ModeDeComposition` — `SERPENT` (défaut) ou `PAR_NIVEAU`.
`TypePhase.POULES` **ne se dédouble pas** : un format de tournoi est de la configuration, pas du
code (règle 2). Les deux modes appellent le même moteur — mêmes rencontres, même barème, même
départage — et ne diffèrent que sur *qui joue avec qui*.

`PAR_NIVEAU` découpe le classement source en **tranches de rangs contiguës**, un groupe par tranche.

### §2 — Le mode commande **aussi** la lecture du classement de phase, et c'est ce qui remplace le décalage par groupe

C'est le cœur de cet ADR. Sous `SERPENT`, le classement de phase se lit « par rang de poule
d'abord » (ADR-0083 §6) : les `P` vainqueurs occupent les rangs `1..P`. Cette règle repose sur une
prémisse — *rien ne rend la poule 1 plus relevée que la poule 2* — que `PAR_NIVEAU` **révoque par
construction**.

Sous `PAR_NIVEAU`, le classement se lit donc **groupe par groupe** : la poule A occupe les rangs 1-6
de la phase, la B les 7-12. Et c'est cette lecture, à elle seule, qui donne à chaque groupe son
propre espace de rangs — le `rang_premier` **unique** de la phase décale ensuite l'ensemble dans
l'espace du tournoi, exactement comme avant.

⚠️ **Un `rang_premier` par groupe n'était donc pas nécessaire, et l'aurait été à tort.** Deux
mécanismes auraient prétendu situer le même archer dans l'espace de rangs du tournoi : l'ordre du
classement de phase, et un décalage porté par le groupe. C'est la définition d'une seconde vérité,
et `DETTE-034` documente déjà ce que coûte d'avoir deux bases pour un même espace de rangs.

**Corollaire — les deux versants sont indissociables.** Composer par tranches en lisant « par rang
de poule d'abord » annoncerait le vainqueur du groupe des 31ᵉ-36ᵉ « 1ᵉʳ du tournoi » : un classement
bien formé, plausible, et faux — la classe de défaut d'ADR-0081. C'est pourquoi le mode voyage
jusqu'à `classement_de_poules` et n'est **pas** consommé seulement à la composition.

**Corollaire — plus aucun bloc indécis inter-poules.** Chaque groupe ayant sa tranche, il n'y a plus
rien à départager *entre* groupes. `departage_inter_poules` devient sans objet sous `PAR_NIVEAU` ; il
est **ignoré, non refusé** — un organisateur qui bascule un réglage existant ne doit pas se voir
opposer un 422 sur une case qu'il n'a pas touchée. Seuls subsistent les ex æquo **internes** à une
poule, que le §10.1 n'a pas séparés.

### §3 — Quand l'effectif ne tombe pas juste, les groupes du **bas** gonflent

`nb_poules_pour` arrondit vers le bas (arbitrage du 09/08/2026, inchangé) : 34 archers en poules de
6 donnent 5 groupes, soit 4 archers à replacer. Ce sont les **dernières** tranches qui gonflent d'une
unité. Les tranches du haut restent à la taille visée : le haut du classement, celui qui a le plus
d'enjeu, tire dans les conditions annoncées plutôt que d'hériter d'un adversaire de plus.

⚠️ **La question ne se posait pas au serpent**, et c'est pourquoi elle n'avait jamais été tranchée :
les groupes y sont équilibrés par construction, donc *lequel* gonfle est sans conséquence sportive.
Par niveau, c'en est une. Arbitrage du commanditaire, cadrage du 21/08/2026.

### §4 — Composer au serpent après des poules est **refusé**, avec dérogation explicite

Une phase de poules qui prélève dans une **autre phase de poules** dispose déjà des niveaux : la
composer au serpent est presque toujours l'inverse de ce que l'organisateur croit régler. La
projection de déroulé produit une anomalie **bloquante** (`SerpentApresDesPoules`), levée par
`ReglageDePoules.serpent_assume`.

**Bloquant plutôt qu'avertissement** — arbitrage du commanditaire, cadrage du 21/08/2026. Le défaut
ne produit ni erreur ni incohérence : il monte un tournoi parfaitement jouable, simplement dépourvu
de l'intérêt sportif visé, et cela ne se voit qu'en salle une fois les groupes affichés. Un
avertissement qu'on peut ignorer arriverait toujours trop tard. Ce que la dérogation achète n'est pas
le droit de se tromper mais la **trace** que le choix a été posé : rebrasser volontairement les
groupes reste légitime, et sans elle « voulu » et « pas vu » sont indiscernables.

⚠️ **Le prédicat porte sur la SOURCE, pas sur le rang dans le déroulé.** Une phase de poules sans
source déclarée est alimentée par le classement du départ (ADR-0068) : ses niveaux viennent de la
qualification, pas des poules qui la précèdent, et le serpent y reste le bon réglage. Lire « la 2ᵉ
phase de poules du déroulé » aurait produit un faux positif systématique sur ce cas — et manqué
celui d'une phase de poules prélevant dans une phase de poules **non adjacente**.

**Structurel, donc bloquant** : les deux vont ensemble, c'est la ligne de partage d'ADR-0063 (« ce
qui est faux quel que soit l'effectif bloque »). Équilibrer des groupes dont les niveaux sont connus
est faux à 12 archers comme à 120.

## Conséquences

- **Aucune migration.** Le réglage de poules vit dans le `config` JSON de l'étape (ADR-0046), pas
  dans une colonne — même propriété que le découpage en tours d'E05US035. Un document écrit avant
  cette US n'a pas la clé et compose au serpent, ce qui est exactement ce qu'il faisait : **aucun
  tournoi déjà réglé ne change de composition**. Le mode n'est écrit qu'à la valeur non-défaut, ce
  qui garde deux documents équivalents identiques.
- **Une valeur de mode inconnue remonte en « configuration illisible »** (ADR-0007) plutôt que de
  retomber sur le serpent : elle ne peut venir que d'une écriture à la main ou d'un retour arrière
  de version, et composer « par prudence » y monterait silencieusement un tournoi que personne n'a
  réglé.
- **La cascade à resserrement tient sans réglage supplémentaire**, et pour une raison qui mérite
  d'être dite : « 3 qualifiés par poule » sur 6 poules prélève 18 archers, soit **trois blocs
  entiers** du classement de phase — le prélèvement ne coupe aucun bloc, donc ADR-0081 ne le refuse
  pas et le départage inter-poules n'est pas requis. Cette propriété tient parce que le nombre de
  qualifiés est **uniforme** ; un resserrement qui couperait un bloc serait refusé et annoncé, ce
  qui est le comportement voulu.
- **Le miroir front de la répartition gagne un second cas.** `frontend/src/shared/phases/poules.ts`
  recopie la règle du domaine (et non son résultat supposé) parce que l'atelier compose un format de
  bibliothèque, sans tournoi, donc sans lecture serveur possible. Le garde-fou reste celui
  d'E05US023 : sa dérive ne produirait qu'un **aperçu** faux, jamais un tournoi faux, puisque c'est
  le serveur qui compose le jour J.
- **`DETTE-054` s'élargit d'un cran** : les deux `ReglagePoulesDTO` jumeaux (`api/v1/phases.py` et
  `api/v1/formats.py`) gagnent chacun les deux mêmes champs. C'est la paire déjà inscrite, pas une
  neuve — la ligne existante est élargie plutôt qu'une dette locale inventée.
- **Ce que cet ADR ne décide pas** : rien sur le croisement des groupes en phase avale
  (`ChocDePoulePossible` reste un avertissement sur les tableaux, inchangé), et rien sur une
  troisième façon de composer. Une politique de composition **injectable** au sens de la règle 2
  n'est pas justifiée aujourd'hui : il y a deux modes, tous deux réclamés par le commanditaire, et
  aucun troisième en vue — la 3ᵉ occurrence n'existe pas.

## Porté dans le code par

⚠️ Section écrite en **vérifiant dans le code du jour**, pas en déduisant de la décision.

| Décision | Module qui l'applique | Vérifié |
|---|---|---|
| §1 — le mode est un réglage, pas un type | `backend/domain/poule.py` (`ModeDeComposition`, `ReglageDePoules.mode`, `ConfigurationPoules.mode`, `pour_effectif`) · `backend/domain/contrat_phase.py` **inchangé** — c'est la vérification : aucun type de phase n'a été ajouté | oui |
| §1 — la composition par tranches contiguës | `backend/domain/poule.py` (`composer_poules`, `_tranches_de_niveau`, `_serpent`) | oui |
| §2 — le mode commande la lecture du classement | `backend/domain/classement_de_poules.py` (`classement_de_poules(mode=…)`, `_par_groupe`, `_en_classement`) | oui |
| §2 — le mode voyage du réglage jusqu'à la lecture | `backend/application/poules.py` (`ServicePoules.classement_de_phase`) | oui |
| §2 — aucun `rang_premier` par groupe | `backend/domain/palmares.py` (`ResultatPhase.rang_premier`) et `backend/application/prelevement.py` (`tranche`) **inchangés** — c'est la vérification | oui |
| §3 — le surplus va aux groupes du bas | `backend/domain/poule.py` (`_tranches_de_niveau`) · miroir `frontend/src/shared/phases/poules.ts` (`repartition`) | oui |
| §4 — le refus, et sa dérogation | `backend/domain/deroule.py` (`_anomalies_serpent_apres_poules`, appelée par `_anomalies_structurelles`) · `backend/domain/erreurs/moteur.py` (`SerpentApresDesPoules`) · `backend/domain/poule.py` (`ReglageDePoules.serpent_assume`) | oui |
| Conséquence — aucune migration, lecture/écriture au `config` JSON | `backend/infrastructure/db/repositories/moteur.py` (`_lire_reglage_poules`, `_mode_de_composition`, écriture dans `_politiques_json`) | oui |
| Conséquence — la frontière API | `backend/api/v1/phases.py` et `backend/api/v1/formats.py` (`ReglagePoulesDTO.mode`, `.serpent_assume`) · `backend/api/v1/poules.py` (`RepartitionReponse.mode`) | oui |
| §1/§3 — la conversion écran ↔ serveur et l'aperçu | `frontend/src/shared/phases/poules.ts` (`ModeDeComposition`, `repartition`, `tranchesDeRangs`, `decrireRepartition`, `versReglage`, `depuisReglage`) | oui |
| §1/§4 — la fiche de réglage, partagée par les deux écrans | `frontend/src/shared/phases/ReglagePoules.tsx` (choix du mode, aide par mode, case de dérogation sous le serpent) | oui |
| §2 — la cascade éprouvée de bout en bout | `backend/tests/test_service_poules_en_cascade.py` | oui |
